#!/usr/bin/env python3
"""Read, write and validate YAML frontmatter of keel handoff files (codec: keel.store.codec).

Values are text; lists are lists of text; nested keys are mappings. An empty value, or one that is only a
comment, is empty text unless block list items follow. A line the codec does not understand is an error
with its line number.

Usage:
  frontmatter.py get <file> <key>
  frontmatter.py set <file> key=value [key=value ...]     (value "[a, b]" becomes a list)
  frontmatter.py validate <file> --type <typ> [--status a,b] [--require k1,k2] [--nonempty k1,k2]
  frontmatter.py dump <file>                               (JSON)
  frontmatter.py find <folder> key=value [key=value ...]   files under folder (recursive, *.md) whose fields all match

Exit codes: 0 ok, 1 validation failed, key missing or nothing found, 2 usage error, unreadable file, unknown syntax or
internal error (System-ADR 0019: a crash must not read as "key missing").
"""
import json
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import KeelError, ParseError, ReadError
from keel.store import codec, frontmatter


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load(path):
    try:
        data, body = frontmatter.load(path)
    except (ReadError, ParseError) as exc:
        fail(str(exc), 2)
    if data is None:
        fail(f"{path}: no frontmatter found", 1)
    return data, body


def cmd_get(args):
    data, _ = load(args[0])
    value = data.get(args[1])
    if value is None:
        sys.exit(1)
    if isinstance(value, dict):
        print(json.dumps(value, ensure_ascii=False))
    else:
        print(", ".join(value) if isinstance(value, list) else value)


def cmd_set(args):
    path = args[0]
    values = {}
    for pair in args[1:]:
        if "=" not in pair:
            fail(f"expected key=value, got {pair}", 2)
        key, value = pair.split("=", 1)
        if value.startswith("[") and value.endswith("]"):
            values[key] = codec.scalar_or_list(value, source="argument")
        else:
            values[key] = value
    load(path)  # missing frontmatter is exit 1, as for get
    try:
        frontmatter.update(path, values)
    except (ReadError, ParseError) as exc:
        fail(str(exc), 2)


def cmd_validate(args):
    path = args[0]
    opts = _opts(args[1:])
    data, _ = load(path)
    errors = []
    typ = opts.get("type")
    if typ and data.get("typ") != typ:
        errors.append(f"typ is '{data.get('typ')}', expected '{typ}'")
    if "status" in opts:
        allowed = opts["status"].split(",")
        if data.get("status") not in allowed:
            errors.append(f"status is '{data.get('status')}', expected one of {', '.join(allowed)}")
    for key in opts.get("require", "").split(","):
        if key and key not in data:
            errors.append(f"missing field '{key}'")
    for key in opts.get("nonempty", "").split(","):
        if key and not data.get(key):
            errors.append(f"field '{key}' is empty")
    if errors:
        fail(f"{path}: " + "; ".join(errors), 1)


def cmd_dump(args):
    data, _ = load(args[0])
    data.pop("__order__", None)
    print(json.dumps(data, ensure_ascii=False))


def cmd_find(args):
    """Every file whose frontmatter has all the given values; a file that cannot be read is exit 2, because an
    answer "not found" could be wrong (System-ADR 0019)."""
    folder = Path(args[0])
    wanted = {}
    for pair in args[1:]:
        if "=" not in pair:
            fail(f"expected key=value, got {pair}", 2)
        key, value = pair.split("=", 1)
        wanted[key] = value
    hits = []
    for p in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        try:
            data = frontmatter.fields(p)
        except (ReadError, ParseError) as exc:
            fail(str(exc), 2)
        if all(str(data.get(k)) == v for k, v in wanted.items()):
            hits.append(str(p))
    if not hits:
        sys.exit(1)
    print("\n".join(hits))


def _opts(args):
    opts = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            opts[args[i][2:]] = args[i + 1] if i + 1 < len(args) else ""
            i += 2
        else:
            i += 1
    return opts


COMMANDS = {"get": cmd_get, "set": cmd_set, "validate": cmd_validate, "dump": cmd_dump, "find": cmd_find}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
        fail(__doc__, 2)
    try:
        COMMANDS[sys.argv[1]](sys.argv[2:])
    except KeelError as exc:
        fail(f"frontmatter: {exc}", exc.exit_code)
    except Exception as exc:  # a crash is exit 2, never the 1 of "key missing" or "invalid"
        fail(f"frontmatter: interner Fehler: {exc!r}", 2)
