#!/usr/bin/env python3
"""Read a value from .keel/config.yaml (codec and schema: keel.store.config).

Usage: config.py <project-dir> <dotted.key> [default]
Prints the value from the file; else the given default; else the schema default. A list or a section prints
the default. Exit 0, or 2 with file and line when the file cannot be read or parsed, or on usage errors.
"""
import sys

import _keel  # noqa: F401
from keel.domain.errors import KeelError
from keel.store import config
from keel.store.paths import Paths


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    project, key = sys.argv[1], sys.argv[2]
    given = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        tree = config.load_file(Paths(project).config)
    except KeelError as exc:
        print(f"config: {exc}", file=sys.stderr)
        return 2
    value = config.lookup(tree, key)
    if value is None or value == "":
        value = given if given is not None else config.default(key)
    print(value if isinstance(value, str) else (given or ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # a crash is exit 2 (System-ADR 0019)
        print(f"config: interner Fehler: {exc!r}", file=sys.stderr)
        sys.exit(2)
