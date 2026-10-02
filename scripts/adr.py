#!/usr/bin/env python3
"""ADRs of a keel project (System-ADR 0021).

Usage:
  adr.py stand <project> <out.json>                 note the ADR state at a role's start (agent-gate.sh)
  adr.py stufe <project> <stand.json> --role <r>    at the role's end: did it write an ADR on a level not its own?
  adr.py neu <project> <slug> [--titel T]           create a new ADR and print its path: numbered on the base
                                                    branch, a draft entwurf-<slug>.md on any other branch
  adr.py check-integration <project> --branch <b>   before integrating b: no Proposed ADR, no numbered new one
  adr.py number <project> [--dry-run]               on the base branch: drafts get the next numbers, references
                                                    under .keel are rewritten
Exit codes (System-ADR 0019): 0 fine, 1 rejected (with the reasons on stdout), 2 cannot check.
"""
import argparse
import json
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import KeelError, UsageError
from keel.services import adr
from keel.store import io


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(f"{message}\n{__doc__}")


def report(problems):
    for p in problems:
        print(p)
    return 1 if problems else 0


def cmd_stand(a):
    io.atomic_write(a.out, json.dumps(adr.snapshot(a.project), ensure_ascii=False))
    return 0


def cmd_stufe(a):
    try:
        before = json.loads(Path(a.stand).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise KeelError(f"ADR-Stand {a.stand} nicht lesbar: {exc}") from exc
    return report(adr.compare(a.project, before, a.role))


def cmd_neu(a):
    print(adr.new_path(a.project, a.slug, a.titel).relative_to(a.project))
    return 0


def cmd_check(a):
    return report(adr.check_integration(a.project, a.branch))


def cmd_number(a):
    plan = adr.number(a.project, dry_run=a.dry_run)
    print(json.dumps(plan, ensure_ascii=False))
    return 0


def build_parser():
    p = _Parser(prog="adr.py", add_help=False)
    sub = p.add_subparsers(dest="cmd", parser_class=_Parser)
    s = sub.add_parser("stand", add_help=False)
    s.add_argument("project", type=Path)
    s.add_argument("out", type=Path)
    s = sub.add_parser("stufe", add_help=False)
    s.add_argument("project", type=Path)
    s.add_argument("stand")
    s.add_argument("--role", required=True)
    s = sub.add_parser("neu", add_help=False)
    s.add_argument("project", type=Path)
    s.add_argument("slug")
    s.add_argument("--titel")
    s = sub.add_parser("check-integration", add_help=False)
    s.add_argument("project", type=Path)
    s.add_argument("--branch", required=True)
    s = sub.add_parser("number", add_help=False)
    s.add_argument("project", type=Path)
    s.add_argument("--dry-run", action="store_true")
    return p


COMMANDS = {"stand": cmd_stand, "stufe": cmd_stufe, "neu": cmd_neu, "check-integration": cmd_check,
            "number": cmd_number}


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
        print(f"adr: {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:  # a crash is "cannot check", never "rejected"
        print(f"adr: interner Fehler: {e!r}", file=sys.stderr)
        sys.exit(2)
