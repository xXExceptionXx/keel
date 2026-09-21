---
name: coach
description: Startet den System-Coach für die Lernschleife. Monatlich oder wenn /keel:kennzahlen Korridorverletzungen zeigt. Aufruf mit /keel:coach. Bericht unter .keel/work/coach/, Vorschläge als Vorlagen in der Inbox.
---

Starte einen frischen Coach und gib nur seine Abschlussnachricht und die Liste der neuen Vorlagen weiter. Du selbst liest keine Kennzahlen und keine Rohdaten.

1. Datum: `date +%F`.
2. Agent-Werkzeug mit `subagent_type` `keel:coach`, Prompt genau eine Zeile: `Datum: <YYYY-MM-DD>`.
3. Danach: `ls .keel/decisions/pending/` und das Frontmatter von `.keel/work/coach/<Datum>.md` über `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py" dump`.
4. `git add .keel/work/coach .keel/decisions && git commit -m "Coach report <Datum>"`.

Melde in höchstens fünf Zeilen: Zahl verletzter Korridore, Zahl der Vorlagen mit ihren Titeln, Pfad des Berichts. Der Mensch entscheidet über `/keel:inbox`.
