#!/usr/bin/env python3
"""Wiedervorlagen (follow-ups) of a keel project, System-ADR 0021.

Usage:
  wiedervorlage.py neu <project> --titel T --frage F --quelle Q [--faellig YYYY-MM-DD] [--vorlage NAME] [--runde 1|2]
      creates .keel/decisions/wiedervorlagen/<heute>-<slug>.md and prints its path
  wiedervorlage.py list <project> [--alle] [--json]
      open follow-ups (--alle: also done ones)
  wiedervorlage.py list <project> --nur-branch <branch> [--json]
      open follow-ups and Vorlagen that exist only on that branch, not on the base branch: before a Vorhaben is
      discarded, each of them is carried over to the base or discarded on purpose
  wiedervorlage.py stand <project>
      the state at the start of a briefing as JSON (skill-gate writes it to state/briefing-<session>.json)
  wiedervorlage.py protokoll <project> --stand <file>
      checks the briefing protocol written since that start; JSON {"ergebnis": offen | ok | fehler | aufgegeben}
      offen: no protocol yet, the briefing is still a conversation. fehler counts up in the state file; from the
      third time on the result is aufgegeben, so the Stop hook lets go and records it instead of looping.
Exit codes (System-ADR 0019): 0 done (list: nothing found with --nur-branch; protokoll: offen, ok, aufgegeben),
1 rejected (invalid fields; --nur-branch: something found; protokoll: fehler), 2 cannot do (usage, files, git).
"""
import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import _keel  # noqa: F401
from keel.domain import adr as adr_rules
from keel.domain import followup
from keel.domain.errors import KeelError, Rejected, UsageError
from keel.integrations import git
from keel.services import agenda
from keel.store import frontmatter, io

FOLDER = Path(".keel") / "decisions" / "wiedervorlagen"
PENDING = Path(".keel") / "decisions" / "pending"


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(f"{message}\n{__doc__}")


def cmd_neu(a):
    today = date.today()
    data = {"typ": followup.TYPE, "titel": a.titel, "frage": a.frage, "quelle": a.quelle,
            "datum": today.isoformat(), "faellig": a.faellig or "", "status": "offen", "ergebnis": "",
            "vorlage": a.vorlage or "", "runde": str(a.runde)}
    problems = followup.validate(data)
    if problems:
        raise Rejected("Wiedervorlage ungültig: " + "; ".join(problems))
    if a.vorlage and not (a.project / PENDING / a.vorlage).is_file():
        raise Rejected(f"Vorlage {a.vorlage} liegt nicht unter {PENDING}")
    body = f"\n# Wiedervorlage: {a.titel}\n\n{a.frage}\n"
    text = frontmatter.render(data, body)
    slug = adr_rules.slugify(a.titel)
    for n in range(1, 100):
        path = a.project / FOLDER / f"{today.isoformat()}-{slug}{'' if n == 1 else f'-{n}'}.md"
        if io.create_exclusive(path, text):
            print(path.relative_to(a.project))
            return 0
    raise KeelError(f"kein freier Dateiname für {slug}")


def cmd_list(a):
    if a.nur_branch:
        return list_branch_only(a)
    rows = []
    for p, f in agenda.followups(a.project):
        if f is None:
            rows.append({"datei": str(p.relative_to(a.project)), "unlesbar": True})
        elif a.alle or followup.is_open(f):
            rows.append({"datei": str(p.relative_to(a.project)), **{k: f.get(k, "") for k in
                         ("titel", "frage", "faellig", "status", "vorlage", "runde")}})
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{r['datei']}: " + ("UNLESBAR" if r.get("unlesbar") else
                                         f"{r['status']}, fällig {r['faellig'] or 'nächstes Briefing'}: {r['titel']}"))
        if not rows:
            print("keine offenen Wiedervorlagen")
    return 0


def list_branch_only(a):
    """Open follow-ups and Vorlagen added on the branch since it left the base."""
    branch = a.nur_branch
    base = git.base(a.project)
    if not git.ref_exists(a.project, branch):
        raise KeelError(f"Branch {branch} gibt es nicht")
    since = git.merge_base(a.project, base, branch)
    rows = []
    for rel in git.diff_names(a.project, since, branch, ".keel/decisions", diff_filter="A"):
        if not rel.endswith(".md") or not (rel.startswith(str(FOLDER)) or rel.startswith(str(PENDING))):
            continue
        data, _ = frontmatter.parse(git.show(a.project, branch, rel) or "", source=f"{branch}:{rel}")
        d = {k: v for k, v in (data or {}).items() if k != "__order__"}
        kind = "wiedervorlage" if rel.startswith(str(FOLDER)) else "vorlage"
        if (kind == "wiedervorlage" and followup.is_open(d)) or \
                (kind == "vorlage" and d.get("status", "offen") in ("offen", agenda.POSTPONED)):
            rows.append({"art": kind, "datei": rel, "titel": d.get("titel", ""), "status": d.get("status", "")})
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{r['art']}: {r['titel']} ({r['datei']}, {r['status']})")
        print(f"{len(rows)} offene Punkt(e) nur auf {branch}: auf {base} übernehmen oder ausdrücklich verwerfen"
              if rows else f"nichts Offenes nur auf {branch}")
    return 1 if rows else 0


SECTION = "## Zurückgestellt"
REF = re.compile(r"wiedervorlagen/([A-Za-z0-9._-]+\.md)")
GIVE_UP_AFTER = 3


def cmd_stand(a):
    today = date.today()
    result = agenda.collect(a.project)
    due = [str(p.relative_to(a.project)) for p, f in agenda.followups(a.project)
           if f is not None and followup.is_due(f, today)]
    postponed = []
    for p in sorted((a.project / PENDING).glob("*.md")) if (a.project / PENDING).is_dir() else []:
        if frontmatter.fields_tolerant(p).get("status") == agenda.POSTPONED:
            postponed.append(p.name)
    print(json.dumps({"start": int(time.time()), "datum": today.isoformat(),
                      "gruende": [r["datei"] for r in result["gruende"] if r["datei"]],
                      "faellige_wiedervorlagen": due, "zurueckgestellt": postponed, "blocks": 0},
                     ensure_ascii=False))
    return 0


def section_lines(body):
    """List items of the section ## Zurückgestellt; None when the section is missing."""
    lines = body.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == SECTION)
    except StopIteration:
        return None
    items = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("- "):
            items.append(line.strip())
    return items


def check_protocol(project, stand, protocol, today):
    problems = []
    data, body = frontmatter.load(protocol)
    data = data or {}
    if data.get("typ") != "briefing" or not data.get("datum"):
        problems.append(f"{protocol.name}: Frontmatter braucht typ: briefing und datum")
    items = section_lines(body)
    if items is None:
        return problems + [f"{protocol.name}: Abschnitt '{SECTION}' fehlt (leer: '- keine')"]
    referenced = set()
    folder = project / FOLDER
    for item in items:
        if item.lower() in ("- keine", "- keine."):
            continue
        refs = REF.findall(item)
        if not refs:
            problems.append(f"{SECTION}: '{item[:60]}' verweist auf keine Wiedervorlage (wiedervorlagen/<datei>.md)")
        for name in refs:
            referenced.add(name)
            f = frontmatter.fields_tolerant(folder / name) if (folder / name).is_file() else None
            if not f:
                problems.append(f"{SECTION}: wiedervorlagen/{name} gibt es nicht oder ist unlesbar")
            elif not followup.is_open(f) or followup.validate(f):
                problems.append(f"{SECTION}: wiedervorlagen/{name} ist nicht offen oder unvollständig")
            elif followup.due_date(f) is not None and followup.due_date(f) <= today:
                problems.append(f"{SECTION}: wiedervorlagen/{name} braucht einen Termin nach heute")
    still = {r["datei"] for r in agenda.collect(project)["gruende"]}
    for datei in stand.get("gruende", []):
        if datei in still:
            problems.append(f"{datei} sperrt noch: entscheiden oder zurückstellen (mit Wiedervorlage)")
    open_for = {}
    for p, f in agenda.followups(project):
        if f is not None and followup.is_open(f) and f.get("vorlage"):
            open_for[str(f["vorlage"])] = p.name
    pending = project / PENDING
    for p in sorted(pending.glob("*.md")) if pending.is_dir() else []:
        if p.name in stand.get("zurueckgestellt", []):
            continue
        if frontmatter.fields_tolerant(p).get("status") == agenda.POSTPONED:
            fu = open_for.get(p.name) or open_for.get(p.stem)
            if fu is None or fu not in referenced:
                problems.append(f"{p.name} ist zurückgestellt: Wiedervorlage anlegen und unter {SECTION} nennen")
    for rel in stand.get("faellige_wiedervorlagen", []):
        f = frontmatter.fields_tolerant(project / rel)
        if followup.is_open(f) and Path(rel).name not in referenced:
            problems.append(f"{rel} war fällig: erledigen (status erledigt, ergebnis) oder unter {SECTION} neu terminieren")
    return problems


def cmd_protokoll(a):
    stand_path = Path(a.stand)
    stand = json.loads(stand_path.read_text(encoding="utf-8"))
    folder = a.project / ".keel" / "work" / "briefing"
    written = [p for p in folder.glob("*.md") if p.stat().st_mtime >= stand.get("start", 0)] if folder.is_dir() else []
    if not written:
        print(json.dumps({"ergebnis": "offen"}))
        return 0
    protocol = max(written, key=lambda p: p.stat().st_mtime)
    problems = check_protocol(a.project, stand, protocol, date.today())
    if not problems:
        print(json.dumps({"ergebnis": "ok", "protokoll": str(protocol.relative_to(a.project))}, ensure_ascii=False))
        return 0
    stand["blocks"] = int(stand.get("blocks", 0)) + 1
    io.atomic_write(stand_path, json.dumps(stand, ensure_ascii=False))
    result = "aufgegeben" if stand["blocks"] > GIVE_UP_AFTER else "fehler"
    print(json.dumps({"ergebnis": result, "protokoll": str(protocol.relative_to(a.project)), "gruende": problems},
                     ensure_ascii=False))
    return 1 if result == "fehler" else 0


def build_parser():
    p = _Parser(prog="wiedervorlage.py", add_help=False)
    sub = p.add_subparsers(dest="cmd", parser_class=_Parser)
    n = sub.add_parser("neu", add_help=False)
    n.add_argument("project", type=Path)
    n.add_argument("--titel", required=True)
    n.add_argument("--frage", required=True)
    n.add_argument("--quelle", required=True)
    n.add_argument("--faellig")
    n.add_argument("--vorlage")
    n.add_argument("--runde", type=int, choices=(1, 2), default=1)
    li = sub.add_parser("list", add_help=False)
    li.add_argument("project", type=Path)
    li.add_argument("--alle", action="store_true")
    li.add_argument("--json", action="store_true")
    li.add_argument("--nur-branch", dest="nur_branch")
    st = sub.add_parser("stand", add_help=False)
    st.add_argument("project", type=Path)
    pr = sub.add_parser("protokoll", add_help=False)
    pr.add_argument("project", type=Path)
    pr.add_argument("--stand", required=True)
    return p


COMMANDS = {"neu": cmd_neu, "list": cmd_list, "stand": cmd_stand, "protokoll": cmd_protokoll}


def main(argv):
    a = build_parser().parse_args(argv)
    if a.cmd not in COMMANDS:
        raise UsageError(__doc__)
    a.project = a.project.resolve()
    return COMMANDS[a.cmd](a)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeelError as e:
        print(f"wiedervorlage: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:  # a crash is "cannot do", never "rejected"
        print(f"wiedervorlage: interner Fehler: {e!r}", file=sys.stderr)
        sys.exit(2)
