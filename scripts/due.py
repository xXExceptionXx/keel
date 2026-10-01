#!/usr/bin/env python3
"""What is due in a keel project, derived from state: briefing, day close-out, audit, coach, architecture round, model switch.

Usage: due.py <project-dir> [--json]
Hard items block all roles except the one that satisfies them; /keel:start runs them in order.
Thresholds in .keel/config.yaml under `faelligkeiten`.
Exit codes (System-ADR 0019): 0 nothing hard is due, 1 something hard is due, 2 cannot tell (usage, internal error).
"""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import read as read_config  # noqa: E402
from frontmatter import parse as parse_fm  # noqa: E402
from models import switches as model_switches  # noqa: E402

DEFAULTS = {"coach_tage": 30, "coach_min_rollenlaeufe": 40, "coach_nach_modellwechsel_rollenlaeufe": 10, "architektur_tage": 7, "architektur_min_commits": 10}


def fm(p):
    d, _ = parse_fm(p.read_text(encoding="utf-8"))
    return d or {}


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout.strip()


def newest(dirpath, pattern="*.md"):
    if not dirpath.exists():
        return None
    files = [p for p in dirpath.glob(pattern) if not p.name.endswith(".bewertung.md")]
    dated = []
    for p in files:
        d = fm(p).get("datum")
        if d:
            try:
                dated.append((date.fromisoformat(d), p))
            except ValueError:
                pass
    return max(dated)[0] if dated else None


class DueError(Exception):
    pass


def event_time(e):
    """Naive UTC datetime of an event, or None when the event has no usable ts."""
    ts = e.get("ts") if isinstance(e, dict) else None
    if not isinstance(ts, str):
        return None
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.astimezone(timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    cfg = read_config(project / ".keel" / "config.yaml") if (project / ".keel" / "config.yaml").exists() else {}
    th = dict(DEFAULTS)
    if isinstance(cfg.get("faelligkeiten"), dict):
        th.update({k: int(v) for k, v in cfg["faelligkeiten"].items() if str(v).isdigit()})
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
    metrics = Path(os.environ.get("KEEL_METRICS_DIR", Path.home() / ".keel-metrics")) / project.name / "events.jsonl"
    runs = 0
    if metrics.exists():
        since = datetime.combine(last_coach, datetime.min.time()) if last_coach else datetime.min
        for line in metrics.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t = event_time(e)
            if t is not None and e.get("event") == "agent_stop" and t >= since:
                runs += 1
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
