#!/usr/bin/env python3
"""Decide whether a morning briefing with the Supervisor is required before the Lead may work.

Usage: briefing_needed.py <project-dir> [--json]
Reasons: supervisor decisions not yet presented (ADRs with entscheider Supervisor and vorgelegt: offen),
Vorlagen escalated as richtungsweisend (eskaliert: Supervisor), Coach Vorlagen, epics in kurskorrektur.
Exit codes (System-ADR 0019): 0 no briefing needed, 1 briefing needed, 2 cannot tell (usage, internal error).
"""
import json
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.store.frontmatter import fields as fm


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    reasons = []
    adr = project / ".keel" / "adr"
    if adr.exists():
        for p in sorted(adr.glob("[0-9]*.md")):
            d = fm(p)
            if d.get("entscheider") == "Supervisor" and str(d.get("vorgelegt", "")).lower() == "offen":
                reasons.append({"art": "supervisor-entscheidung", "datei": str(p.relative_to(project)), "titel": d.get("titel", "")})
    pending = project / ".keel" / "decisions" / "pending"
    if pending.exists():
        for p in sorted(pending.glob("*.md")):
            d = fm(p)
            if d.get("eskaliert") == "Supervisor":
                reasons.append({"art": "richtungsweisend", "datei": str(p.relative_to(project)), "titel": d.get("titel", "")})
            elif d.get("von") == "Coach":
                reasons.append({"art": "coach-vorlage", "datei": str(p.relative_to(project)), "titel": d.get("titel", "")})
    epics = project / ".keel" / "work" / "epics"
    if epics.exists():
        for p in sorted(epics.glob("*.md")):
            if p.name.endswith(".bewertung.md"):
                continue
            d = fm(p)
            if d.get("status") == "kurskorrektur":
                reasons.append({"art": "kurskorrektur", "datei": str(p.relative_to(project)), "titel": d.get("titel", "")})
    if "--json" in sys.argv:
        print(json.dumps({"briefing_noetig": bool(reasons), "gruende": reasons}, ensure_ascii=False, indent=2))
    else:
        if reasons:
            print(f"Briefing nötig ({len(reasons)}):")
            for r in reasons:
                print(f"  {r['art']}: {r['titel']} ({r['datei']})")
        else:
            print("kein Briefing nötig")
    sys.exit(1 if reasons else 0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a crash must not read as "briefing needed" (exit 1)
        print(f"briefing_needed: interner Fehler: {e!r}", file=sys.stderr)
        sys.exit(2)
