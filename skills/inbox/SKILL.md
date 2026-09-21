---
name: inbox
description: Zeigt die Entscheidungs-Inbox des Menschen. Offene Vorlagen, Pläne zur Abnahme, blockierte Vorhaben und der letzte Prüfbericht, alles nur aus Frontmatter. Aufruf mit /keel:inbox.
---

Zeige dem Menschen, was auf seine Entscheidung wartet. Lies nur Frontmatter über `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py" dump <datei>`, keine Bodies, keinen Code.

Sammle:

1. **Vorlagen:** alle Dateien unter `.keel/decisions/pending/`. Je Vorlage: Titel, von, Datum. Für jede gib zusätzlich die Zeilen **Empfehlung** und **Warum ich nicht selbst entscheide** aus dem Body wörtlich wieder; das ist die einzige Ausnahme von der Frontmatter-Regel, weil der Mensch damit in einer Minute entscheiden soll.
2. **Zur Abnahme:** Pläne unter `.keel/work/plans/` mit Status `abnahme-bereit` oder `abnahme-rot`, mit Pfad des Abnahmenachweises unter `.keel/work/acceptance/`.
3. **Blockiert:** Pläne mit Status `blockiert` oder `strukturaenderung`, Aufgaben mit Status `neuschnitt`, `testeinspruch`, `budget-erschoepft`, `reparatur`.
4. **Letzter Prüfbericht:** neueste Datei unter `.keel/work/audit/`, Status und Datum.
5. **Delegierte ADRs:** Dateien unter `.keel/adr/` mit Status `Accepted (delegiert)`, die jünger als sieben Tage sind.

Gib eine kompakte Übersicht in dieser Reihenfolge aus, je Punkt eine Zeile, leere Abschnitte mit „keine“. Danach in einem Satz, was der Mensch tun kann: Eine Vorlage entscheidet er, indem er im Frontmatter `status: entschieden` und `entscheidung: <Nummer der Option>` setzt und die Datei nach `.keel/decisions/done/` verschiebt. Einen Plan nimmt er ab, indem er `status: abgenommen` setzt. Eine Blockade hebt er auf, indem er den Plan-Status auf `in-arbeit` setzt, nachdem er die Ursache behoben hat.
