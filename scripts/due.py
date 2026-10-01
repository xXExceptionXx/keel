#!/usr/bin/env python3
"""What is due in a keel project, derived from state: briefing, day close-out, audit, coach, architecture round, model switch.

Usage: due.py <project-dir> [--json]
Hard items block all roles except the one that satisfies them; /keel:start runs them in order.
Thresholds in .keel/config.yaml under `faelligkeiten`.
Exit codes (System-ADR 0019): 0 nothing hard is due, 1 something hard is due, 2 cannot tell (usage, internal error).
"""
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import _keel  # noqa: F401
from keel.store import config, events, frontmatter
from keel.store.paths import Paths
from models import switches as model_switches  # noqa: E402

THRESHOLDS = ("coach_tage", "coach_min_rollenlaeufe", "coach_nach_modellwechsel_rollenlaeufe", "architektur_tage",
              "architektur_min_commits")


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout.strip()


def newest(dirpath, pattern="*.md"):
    if not dirpath.exists():
        return None
    files = [p for p in dirpath.glob(pattern) if not p.name.endswith(".bewertung.md")]
    dated = []
    for p in files:
        d = frontmatter.fields(p).get("datum")
        if d:
            try:
                dated.append((date.fromisoformat(d), p))
            except ValueError:
                pass
    return max(dated)[0] if dated else None


class DueError(Exception):
    pass


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    paths = Paths(project)
    cfg = config.load_file(paths.config)
    th = {k: config.get_int(cfg, f"faelligkeiten.{k}") for k in THRESHOLDS}
    today = date.today()
    items = []

    # briefing
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "briefing_needed.py"), str(project), "--json"], capture_output=True, text=True)
    try:
        br = json.loads(r.stdout) if r.returncode in (0, 1) else None
    except ValueError:
        br = None
    if not isinstance(br, dict):
        raise DueError(f"briefing_needed.py endete mit {r.returncode}: {r.stderr.strip()[-300:]}")
    if br.get("briefing_noetig"):
        items.append({"art": "briefing", "hart": True, "rolle": "supervisor", "grund": f"{len(br['gruende'])} Punkt(e) für das Briefing", "befehl": "/keel:start (wird zum Briefing)"})

    # day close-out: commits after the last day tag from a day before today
    last_tag = sh(["git", "tag", "-l", "day-*", "--sort=-creatordate"], project).split("\n")[0] if sh(["git", "tag", "-l", "day-*"], project) else ""
    rng = f"^{last_tag}" if last_tag else ""
    log = sh(["git", "log", "--all", "--format=%cs", rng, "--", ".", ":(exclude).keel"], project) if last_tag else sh(["git", "log", "--all", "--format=%cs", "--", ".", ":(exclude).keel"], project)
    commit_days = sorted({d for d in log.split("\n") if d})
    stale_days = [d for d in commit_days if d < today.isoformat()]
    if stale_days:
        items.append({"art": "tagesabschluss", "hart": True, "rolle": "lead", "grund": f"Arbeit vom {stale_days[0]} ohne Tagesabschluss ({len(log.split())} Commits seit {last_tag or 'Beginn'})", "befehl": "/keel:start holt ihn nach"})

    # audit: newest day tag newer than newest audit report
    if last_tag:
        tag_date = sh(["git", "log", "-1", "--format=%cs", last_tag], project)
        last_audit = newest(project / ".keel" / "work" / "audit")
        if tag_date and (last_audit is None or last_audit < date.fromisoformat(tag_date)):
            items.append({"art": "audit", "hart": True, "rolle": "auditor", "grund": f"Tag {last_tag} ohne Prüfbericht", "befehl": "/keel:start führt ihn aus"})

    # coach: enough days and enough role runs since the last report
    last_coach = newest(project / ".keel" / "work" / "coach")
    # report dates are local calendar days; events carry UTC: the day starts at local midnight
    since = datetime.combine(last_coach, datetime.min.time()).astimezone() if last_coach else None
    runs = sum(1 for e in events.read(paths.events, since=since).events if e.get("event") == "agent_stop")
    days = (today - last_coach).days if last_coach else None
    if (days is None or days >= th["coach_tage"]) and runs >= th["coach_min_rollenlaeufe"]:
        items.append({"art": "coach", "hart": True, "rolle": "coach", "grund": f"{days if days is not None else 'noch kein'} Tage seit dem letzten Coach-Lauf, {runs} Rollenläufe seitdem", "befehl": "/keel:start führt ihn aus"})
    elif runs >= th["coach_min_rollenlaeufe"] and days is not None:
        items.append({"art": "coach", "hart": False, "rolle": "coach", "grund": f"{runs} Rollenläufe seit dem letzten Lauf, fällig in {th['coach_tage'] - days} Tagen", "befehl": "/keel:coach"})

    # model switch: a role runs on a new model. Hint right away; the Coach is due early once enough runs on the
    # new model allow a comparison, regardless of coach_tage. Settled by `modell_geprueft` in a Coach report.
    for sw in model_switches(project):
        what = f"Modellwechsel auf {sw['modell']} seit {sw['seit']} (vorher {', '.join(sw['vorher'])}; Rollen: {', '.join(sw['rollen'])})"
        need = th["coach_nach_modellwechsel_rollenlaeufe"]
        if sw["laeufe"] >= need:
            coach = next((i for i in items if i["art"] == "coach"), None)
            if coach and coach["hart"]:
                coach["grund"] += f"; {what}"
            else:
                if coach:
                    items.remove(coach)
                items.append({"art": "coach", "hart": True, "rolle": "coach", "grund": f"{what}, {sw['laeufe']} Rollenläufe auf dem neuen Modell", "befehl": "/keel:start führt ihn aus"})
        else:
            items.append({"art": "modellwechsel", "hart": False, "rolle": "coach", "grund": f"{what}; {sw['laeufe']} von {need} Rollenläufen für den Vergleich, danach wird der Coach fällig", "befehl": "weiterarbeiten"})

    # architecture round: days and commits since the last report
    last_arch = newest(project / ".keel" / "work" / "architektur")
    since_arg = f"--since={last_arch.isoformat()}" if last_arch else "--since=1970-01-01"
    commits = len([l for l in sh(["git", "log", "--all", "--format=%h", since_arg, "--", ".", ":(exclude).keel"], project).split("\n") if l])
    adays = (today - last_arch).days if last_arch else None
    if (adays is None or adays >= th["architektur_tage"]) and commits >= th["architektur_min_commits"]:
        items.append({"art": "architektur", "hart": True, "rolle": "architekt", "grund": f"{adays if adays is not None else 'noch keine'} Tage seit der letzten Wochenrunde, {commits} Commits seitdem", "befehl": "/keel:start führt sie aus"})

    # soft: inbox items
    pending = project / ".keel" / "decisions" / "pending"
    n_pending = len(list(pending.glob("*.md"))) if pending.exists() else 0
    if n_pending and not br.get("briefing_noetig"):
        items.append({"art": "vorlagen", "hart": False, "rolle": "supervisor", "grund": f"{n_pending} offene Vorlage(n), der Supervisor entscheidet sie beim Start", "befehl": "/keel:start"})

    hard = [i for i in items if i["hart"]]
    if "--json" in sys.argv:
        print(json.dumps({"hart": bool(hard), "faellig": items}, ensure_ascii=False, indent=2))
    else:
        if not items:
            print("nichts fällig")
        for i in items:
            print(f"{'HART' if i['hart'] else 'soft'}  {i['art']}: {i['grund']} → {i['befehl']}")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    try:
        main()
    except DueError as e:
        print(f"due: nicht prüfbar: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # a crash must not read as "something is due" (exit 1)
        print(f"due: interner Fehler: {e!r}", file=sys.stderr)
        sys.exit(2)
