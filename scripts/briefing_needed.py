#!/usr/bin/env python3
"""Decide whether a morning briefing with the Supervisor is required before the Lead may work, and what is on its agenda.

Usage: briefing_needed.py <project-dir> [--json] [--voll]
Blocking reasons (gruende): supervisor decisions not yet presented, Vorlagen escalated as richtungsweisend, Coach
Vorlagen of the project level, postponed Vorlagen whose follow-up is due the second time or that lost their
follow-up, follow-ups far past their date, epics in kurskorrektur.
Agenda (tagesordnung, never blocking): due follow-ups, postponed Vorlagen due the first time, Audit backlog items
waiting for a decision, Proposed ADRs on the base branch, motor proposals of the Coach, passed-on motor proposals
nobody decided within 30 days (System-ADR 0021). --voll also asks a GitHub backlog; without it only a local one.
Exit codes (System-ADR 0019): 0 no briefing needed, 1 briefing needed, 2 cannot tell (usage, internal error).
"""
import json
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import KeelError
from keel.services import agenda


def backlog_items(project, full):
    """Backlog items for the agenda; a text when the backlog cannot be read, None when it is not asked."""
    import backlog
    try:
        from keel.store import config
        cfg = config.section(config.load(project), "backlog")
        provider = cfg.get("provider") or "markdown"
        if provider != "markdown" and not full:
            return None
        return backlog.ADAPTERS[provider](project, cfg).list("vorgeschlagen")
    except (KeelError, OSError, ValueError, KeyError, SystemExit) as exc:
        return f"{type(exc).__name__}: {exc}"


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    result = agenda.collect(project, backlog_items=backlog_items(project, "--voll" in sys.argv))
    reasons, items = result["gruende"], result["tagesordnung"]
    if "--json" in sys.argv:
        print(json.dumps({"briefing_noetig": bool(reasons), "gruende": reasons, "tagesordnung": items},
                         ensure_ascii=False, indent=2))
    else:
        if reasons:
            print(f"Briefing nötig ({len(reasons)}):")
            for r in reasons:
                print(f"  {r['art']}: {r['titel']} ({r['datei'] or r.get('grund', '')})")
        else:
            print("kein Briefing nötig")
        if items:
            print(f"Tagesordnung ({len(items)}):")
            for r in items:
                print(f"  {r['art']}: {r['titel']}" + (f" ({r['datei']})" if r["datei"] else "")
                      + (f": {r['grund']}" if r.get("grund") else ""))
    sys.exit(1 if reasons else 0)


if __name__ == "__main__":
    try:
        main()
    except KeelError as e:  # an unreadable artifact: cannot tell, and say which file and line
        print(f"briefing_needed: nicht prüfbar: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # a crash must not read as "briefing needed" (exit 1)
        print(f"briefing_needed: interner Fehler: {e!r}", file=sys.stderr)
        sys.exit(2)
