#!/usr/bin/env python3
"""Merge keel's permission deny rules into a project's .claude/settings.json.

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
    rules = json.loads(deny_path.read_text(encoding="utf-8"))["permissions"]["deny"]

    permissions = settings.setdefault("permissions", {})
    deny = permissions.setdefault("deny", [])
    added = [r for r in rules if r not in deny]
    deny.extend(added)

    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"deny rules: {len(added)} added, {len(deny) - len(added)} already present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
