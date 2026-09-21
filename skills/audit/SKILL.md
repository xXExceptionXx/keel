---
name: audit
description: Startet den Auditor für den Tageslauf, mit "woche" für den Wochenlauf gegen den Gesamtstand. Aufruf mit /keel:audit oder /keel:audit woche. Der Prüfbericht landet unter .keel/work/audit/.
---

Starte einen frischen Auditor und gib nur seinen Bericht in Kurzform weiter. Du selbst liest weder Diff noch Code.

1. Bestimme das Datum: `date +%F`. Wechsle keinen Branch; geprüft wird der aktive Branch, auf dem gearbeitet wurde.
2. Starte das Agent-Werkzeug mit `subagent_type` `keel:auditor`. Prompt, erste Zeile `Datum: <YYYY-MM-DD>`; ist `$ARGUMENTS` gleich `woche`, zweite Zeile `Modus: woche`. Mehr nicht.
3. Lies danach nur das Frontmatter des Berichts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py" dump .keel/work/audit/<Datum>.md` beziehungsweise `woche-<Datum>.md`, und gib die Abschnitte **Abweichungen** und **Delegierte Entscheidungen zur Durchsicht** wörtlich wieder. Sie sind für den Menschen bestimmt.
4. Committe den Bericht: `git add .keel/work/audit && git commit -m "Prüfbericht <Datum>"`.

Melde in höchstens fünf Zeilen: Status, Zahl der Abweichungen, Zahl der ADRs zur Durchsicht, Pfad des Berichts.
