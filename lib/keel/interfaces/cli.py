"""Command line `keel` (bin/keel). Interfaces hold no logic; they call store and services.

  keel --version
  keel doctor [--project DIR] [--json]
  keel path [--project DIR] [--ensure] (root|runtime|state|logs|events|hooklog|brake | --shell)

Exit codes (System-ADR 0019): 0 ok, 1 findings, 2 usage or internal error.
"""
import argparse
import shlex
import sys

import keel
from keel.domain.errors import KeelError, UsageError
from keel.store.paths import Paths

PATH_NAMES = ("brake", "events", "hooklog", "logs", "root", "runtime", "state")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def build_parser():
    p = _Parser(prog="keel", description="keel core")
    p.add_argument("--version", action="version", version=f"keel {keel.__version__}")
    sub = p.add_subparsers(dest="command")

    d = sub.add_parser("doctor", help="check project and machine")
    d.add_argument("--project", default=".")
    d.add_argument("--json", action="store_true")

    pa = sub.add_parser("path", help="paths of the runtime folder")
    pa.add_argument("--project", default=".")
    pa.add_argument("--ensure", action="store_true", help="create the runtime folders")
    pa.add_argument("--shell", action="store_true", help="all paths as shell assignments for eval")
    pa.add_argument("name", nargs="?", choices=PATH_NAMES)
    return p


def cmd_doctor(args):
    import json

    from keel.services import doctor  # loaded only here: `keel path` runs in every hook and must start fast

    findings = doctor.run(args.project)
    ok = doctor.healthy(findings)
    if args.json:
        print(json.dumps({"projekt": str(Paths(args.project).project), "gesund": ok,
                          "befunde": [f.as_dict() for f in findings]}, ensure_ascii=False, indent=2))
    else:
        print(f"keel doctor: {Paths(args.project).project}")
        for f in findings:
            print(f"  {f.stufe.upper() if f.stufe != doctor.OK else 'ok':8} {f.pruefung:14} {f.meldung}")
    return 0 if ok else 1


def cmd_path(args):
    paths = Paths(args.project)
    if args.ensure:
        paths.ensure()
    named = paths.by_name()
    if args.shell:
        for name, value in named.items():
            print(f"KEEL_PATH_{name.upper()}={shlex.quote(str(value))}")
        return 0
    if not args.name:
        raise UsageError("keel path: Name oder --shell angeben")
    print(named[args.name])
    return 0


COMMANDS = {"doctor": cmd_doctor, "path": cmd_path}


def main(argv=None):
    try:
        args = build_parser().parse_args(argv)
        if not args.command:
            raise UsageError(__doc__.strip())
        return COMMANDS[args.command](args)
    except KeelError as exc:
        print(f"keel: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # a crash is exit 2, never a finding (System-ADR 0019)
        print(f"keel: interner Fehler: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
