#!/usr/bin/env python3
"""Read a value from .keel/config.yaml without PyYAML (two levels, scalars only).

Usage: config.py <project-dir> <dotted.key> [default]
"""
import re
import sys
from pathlib import Path


def read(path):
    tree = {}
    section = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(\s*)([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if not m:
            continue
        indent, key, value = len(m.group(1)), m.group(2), m.group(3).strip()
        if indent == 0:
            if value == "":
                section = key
                tree.setdefault(key, {})
            else:
                section = None
                tree[key] = _unquote(value)
        elif section is not None and value != "":
            tree[section][key] = _unquote(value)
    return tree


def _unquote(v):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def main():
    project, key = sys.argv[1], sys.argv[2]
    default = sys.argv[3] if len(sys.argv) > 3 else ""
    path = Path(project) / ".keel" / "config.yaml"
    tree = read(path) if path.exists() else {}
    node = tree
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            print(default)
            return
    print(node if isinstance(node, str) else default)


if __name__ == "__main__":
    main()
