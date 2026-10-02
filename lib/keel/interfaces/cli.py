"""Command line `keel` (bin/keel). Interfaces hold no logic; they call store and services.

  keel --version
  keel doctor [--project DIR] [--json]
  keel path [--project DIR] [--ensure] (root|runtime|state|logs|events|hooklog|brake | --shell)
  keel motor add [--project DIR] --typ motorvorschlag|motorbefund --titel T [--hypothese H] [--kennzahlen K]
                 [--quelle-vorlage V] < text      a proposal or finding for the plugin, into the machine-wide inbox
  keel motor list [--status S] [--json]           the inbox (~/.keel-metrics/motor/), for a session in the keel repo
  keel motor show <id>
  keel motor set <id> key=value ...               status (offen|angenommen|abgelehnt|umgesetzt), system_adr, ...

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

    m = sub.add_parser("motor", help="machine-wide inbox for motor proposals and findings")
    msub = m.add_subparsers(dest="action")
    ma = msub.add_parser("add")
    ma.add_argument("--project", default=".")
    ma.add_argument("--typ", required=True)
    ma.add_argument("--titel", required=True)
    ma.add_argument("--hypothese", default="")
    ma.add_argument("--kennzahlen", default="")
    ma.add_argument("--quelle-vorlage", dest="quelle_vorlage", default="")
    ml = msub.add_parser("list")
    ml.add_argument("--status")
    ml.add_argument("--json", action="store_true")
    ms = msub.add_parser("show")
    ms.add_argument("id")
    mt = msub.add_parser("set")
    mt.add_argument("id")
    mt.add_argument("values", nargs="+")
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


def cmd_motor(args):
    import json

    from keel.services import motor

    if args.action == "add":
        body = sys.stdin.read()
        print(motor.add(args.project, args.typ, args.titel, body, args.hypothese, args.kennzahlen,
                        args.quelle_vorlage))
    elif args.action == "list":
        rows = motor.entries(args.status)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        for r in [] if args.json else rows:
            print(f"{r['id']}: " + ("UNLESBAR" if r.get("unlesbar") else
                                     f"{r['status']}, {r['typ']}, {r['projekt']}, {r['plugin_version']}: {r['titel']}"))
        if not rows and not args.json:
            print("keine Einträge")
    elif args.action == "show":
        print(motor.show(args.id), end="")
    elif args.action == "set":
        values = {}
        for pair in args.values:
            key, sep, value = pair.partition("=")
            if not sep:
                raise UsageError(f"{pair!r} ist nicht key=value")
            values[key] = value
        motor.set_fields(args.id, values)
    else:
        raise UsageError("keel motor add|list|show|set")
    return 0


COMMANDS = {"doctor": cmd_doctor, "path": cmd_path, "motor": cmd_motor}


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
