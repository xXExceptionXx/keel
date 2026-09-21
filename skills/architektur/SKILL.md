---
name: architektur
description: Startet den Architekten für die Bestandsaufnahme eines bestehenden Projekts oder die wöchentliche Drift-Runde. Aufruf mit /keel:architektur bestand oder /keel:architektur woche.
---

Starte einen frischen Architekten und gib nur seine Abschlussnachricht weiter. Du selbst liest keinen Code.

1. Modus aus `$ARGUMENTS`: `bestand` oder `woche` (Standard `woche`). Datum: `date +%F`.
2. Agent-Werkzeug mit `subagent_type` `keel:architekt`, `run_in_background: false`, Prompt: erste Zeile `Anlass: bestandsaufnahme` beziehungsweise `Anlass: wochenrunde`, zweite Zeile `Datum: <YYYY-MM-DD>`.
3. Danach Frontmatter des Berichts unter `.keel/work/architektur/` lesen (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py" dump`), bei `bestand` zusätzlich `ls .keel/adr/`.
4. `git add .keel && git commit -m "Architecture report <Datum>"`.

Melde in höchstens fünf Zeilen: Modus, Status, Zahl der Befunde, bei Bestandsaufnahme die Zahl der ADR-Entwürfe. Befunde werden am nächsten Tagesstart geroutet, ADR-Entwürfe zeigt `/keel:inbox`.
