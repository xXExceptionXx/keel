#!/usr/bin/env python3
"""Merge keel's permission allow and deny rules into a project's .claude/settings.json.

Usage: merge_settings.py <settings.json> <deny.json>
Existing entries are kept; keel's rules are added if missing. Order is preserved.
"""
import json
import sys
from pathlib import Path


def main() -> int:
    settings_path = Path(sys.argv[1])
    deny_path = Path(sys.argv[2])

    settings = json.loads(settings_path.read_text(encoding="utf-8") or "{}")
    wanted = json.loads(deny_path.read_text(encoding="utf-8"))["permissions"]
    permissions = settings.setdefault("permissions", {})
    for kind in ("allow", "deny"):
        rules = wanted.get(kind, [])
        current = permissions.setdefault(kind, [])
        added = [r for r in rules if r not in current]
        current.extend(added)
        print(f"{kind} rules: {len(added)} added, {len(current) - len(added)} already present")

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
