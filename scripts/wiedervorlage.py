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
Exit codes (System-ADR 0019): 0 done (list: nothing found with --nur-branch), 1 rejected (invalid fields;
--nur-branch: something found), 2 cannot do (usage, unreadable files, git).
"""
import argparse
import json
import sys
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
    return p


COMMANDS = {"neu": cmd_neu, "list": cmd_list}


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
