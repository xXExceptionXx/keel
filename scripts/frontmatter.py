#!/usr/bin/env python3
"""Read, write and validate YAML frontmatter of keel handoff files.

No PyYAML dependency: supports scalars, inline lists `[a, b]` and block lists
(`- item`). Values are kept as strings; lists as lists of strings. An empty value,
or one that is only a comment, is empty text unless block list items follow.

Usage:
  frontmatter.py get <file> <key>
  frontmatter.py set <file> key=value [key=value ...]     (value "[a, b]" becomes a list)
  frontmatter.py validate <file> --type <typ> [--status a,b] [--require k1,k2] [--nonempty k1,k2]
  frontmatter.py dump <file>                               (JSON)

Exit codes: 0 ok, 1 validation failed, 2 usage or file error.
"""
import json
import re
import sys
from pathlib import Path

DELIM = "---"


def parse(text):
    if not text.startswith(DELIM + "\n"):
        return None, text
    end = text.find("\n" + DELIM + "\n", len(DELIM) + 1)
    if end < 0:
        if text.rstrip("\n").endswith("\n" + DELIM) or text.rstrip("\n") == DELIM:
            end = len(text.rstrip("\n")) - len(DELIM) - 1
        else:
            return None, text
    header = text[len(DELIM) + 1 : end]
    body = text[end + len(DELIM) + 2 :]
    data = {}
    order = []
    current_list = None
    for raw in header.split("\n"):
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if current_list is not None and re.match(r"^\s*-(\s|$)", line):
            # an empty key followed by "- item" lines (indented or not) is a block list
            if not isinstance(data[current_list], list):
                data[current_list] = []
            data[current_list].append(_scalar(re.sub(r"^\s*-\s*", "", line)))
            continue
        current_list = None
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        order.append(key)
        if value == "" or value.startswith("#"):
            # empty, or only a comment: empty text unless block list items follow
            data[key] = ""
            current_list = key
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_scalar(v) for v in _split_inline(inner)] if inner else []
        else:
            data[key] = _scalar(value)
    data["__order__"] = order
    return data, body


def _split_inline(inner):
    return [p.strip() for p in re.split(r",(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)", inner) if p.strip()]


def _scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        # written by _quote with json.dumps: unescape, so reading and writing do not add backslashes
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return re.sub(r"\s+#.*$", "", value)


def render(data, body):
    order = data.get("__order__", [k for k in data if k != "__order__"])
    keys = [k for k in order if k in data] + [k for k in data if k not in order and k != "__order__"]
    lines = [DELIM]
    for key in keys:
        value = data[key]
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            elif all(_simple(v) for v in value):
                lines.append(f"{key}: [{', '.join(value)}]")
            else:
                lines.append(f"{key}:")
                lines.extend(f"  - {_quote(v)}" for v in value)
        else:
            lines.append(f"{key}: {_quote(value)}")
    lines.append(DELIM)
    return "\n".join(lines) + "\n" + body


def _simple(v):
    return re.fullmatch(r"[A-Za-z0-9_./#@:-]+", v) is not None


def _quote(v):
    v = str(v)
    if v == "" or re.search(r"[:#\[\]{}\"\\]|^['\s]|\s$", v) or v.lower() in {"true", "false", "null", "yes", "no"}:
        return json.dumps(v, ensure_ascii=False)
    return v


def load(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}", 2)
    data, body = parse(text)
    if data is None:
        fail(f"{path}: no frontmatter found", 1)
    return data, body


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def cmd_get(args):
    data, _ = load(args[0])
    value = data.get(args[1])
    if value is None:
        sys.exit(1)
    print(", ".join(value) if isinstance(value, list) else value)


def cmd_set(args):
    path = args[0]
    data, body = load(path)
    for pair in args[1:]:
        if "=" not in pair:
            fail(f"expected key=value, got {pair}", 2)
        key, value = pair.split("=", 1)
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_scalar(v) for v in _split_inline(inner)] if inner else []
        else:
            data[key] = value
        if key not in data["__order__"]:
            data["__order__"].append(key)
    Path(path).write_text(render(data, body), encoding="utf-8")


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


COMMANDS = {"get": cmd_get, "set": cmd_set, "validate": cmd_validate, "dump": cmd_dump}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
        fail(__doc__, 2)
    COMMANDS[sys.argv[1]](sys.argv[2:])
