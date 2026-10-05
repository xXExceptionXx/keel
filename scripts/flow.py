#!/usr/bin/env python3
"""The flow rules of keel in one place: when a role may start, and who acts next.

Usage: flow.py bereit <project>    JSON: per role the objects it could start on now (for the monitor)

The tables (GATES, DUE_ROLES, PHASES, NEXT_*) live in keel.domain.flow; this script adds what reads the
project: which objects a role could start on now (for the monitor).
"""
import json
import re
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.flow import (BY_DUE, DUE_ROLES, GATES, NEXT_AFTER_REVIEW, NEXT_PLAN, NEXT_TASK,  # noqa: F401
                              PHASES, ROLES, next_task)
from keel.store.frontmatter import load_tolerant


def _objects(keel, kind, unreadable=None):
    """Objects of a kind with their frontmatter; files the codec refuses go to unreadable instead of vanishing."""
    folder = {"plan": "work/plans", "aufgabe": "work/tasks", "epic": "work/epics", "vorlage": "decisions/pending"}[kind]
    d = keel / folder
    for p in sorted(d.glob("*.md")) if d.exists() else []:
        if p.name.endswith(".bewertung.md"):
            continue
        loaded = load_tolerant(p)
        if loaded is None:
            if unreadable is not None:
                unreadable.add(p)
            continue
        data, body = loaded
        typ = {"aufgabe": "aufgabe", "plan": "plan", "epic": "epic", "vorlage": "vorlage"}[kind]
        if data.get("typ") != typ:
            continue
        name = data.get("id") if kind == "aufgabe" and data.get("id") else p.stem
        yield name, p, data, body


def _empty(v):
    return v is None or v == "" or v == []


def satisfied(keel, g, name, path, data, body):
    """Whether an existing object meets the entry condition of a gate entry."""
    if g.get("status") and data.get("status") not in g["status"]:
        return False
    if any(_empty(data.get(k)) for k in g.get("nonempty", [])):
        return False
    if any(str(data.get(k, "")) != v for k, v in g.get("feld", {}).items()):
        return False
    if any(not _empty(data.get(k)) for k in g.get("nicht", [])):
        return False
    if g.get("abschnitt") and not re.search(rf"^{re.escape(g['abschnitt'])}", body, re.M):
        return False
    if g.get("datei") and not (keel / g["datei"].format(name=name)).is_file():
        return False
    return True


def bereit(project):
    """Per role: the objects it could start on now, by the gate's entry conditions. Roles that start by
    due item (auditor, coach) or by date (architect rounds) are left to the due list. Under "unlesbar": files
    whose frontmatter cannot be read, so they cannot be ready for anyone (keel doctor names the line)."""
    keel = Path(project) / ".keel"
    out = {r: [] for r in ROLES}
    unreadable = set()
    for key, g in GATES.items():
        if g.get("nur_gate") or g.get("oder_fehlt"):
            continue
        role, anlass = key.split(".", 1)
        for name, path, data, body in _objects(keel, g["objekt"], unreadable):
            if satisfied(keel, g, name, path, data, body):
                out[role].append({"anlass": anlass, "ref": name, "pfad": str(path.relative_to(project))})
    out["unlesbar"] = sorted(str(p.relative_to(project)) for p in unreadable)
    return out


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "bereit":
        print(json.dumps(bereit(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
