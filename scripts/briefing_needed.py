#!/usr/bin/env python3
"""Decide whether a morning briefing with the Supervisor is required before the Lead may work.

Usage: briefing_needed.py <project-dir> [--json]
Reasons: supervisor decisions not yet presented (ADRs with entscheider Supervisor and vorgelegt: offen),
Vorlagen escalated as richtungsweisend (eskaliert: Supervisor), Coach Vorlagen, epics in kurskorrektur.
Exit 1 when a briefing is needed, 0 otherwise.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from frontmatter import parse as parse_fm  # noqa: E402


def fm(p):
    d, _ = parse_fm(p.read_text(encoding="utf-8"))
    return d or {}


def main():
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
    main()
