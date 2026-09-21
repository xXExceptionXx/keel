---
nummer: 0005
titel: Lernschleife: Kennzahlen aus Artefakten, Coach als Rolle, Backlog-Port, Kontext-Alarm
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes:
hypothese: Der Coach findet nach dem ersten Monat mindestens eine Justierung mit messbarer Wirkung; die Korridore aus dem Konzept müssen zu mindestens einem Drittel kalibriert werden
---

# 0005: Lernschleife

## Kontext

Das Konzept verlangt, dass das System sich selbst misst, ohne dass Rollen Kennzahlen melden, dass ein Coach Justierungen mit Hypothese vorschlägt, und dass das Backlog hinter einer Schnittstelle liegt.

## Entscheidung

- **Kennzahlen** berechnet `scripts/metrics.py` aus Artefakten und Rohdaten: Aufgaben-, Review-, Audit- und Entscheidungsdateien, Git-Log mit `Keel-Task`, `events.jsonl` der Hooks und die Subagent-Transkripte für Tokens. Korridore stehen in `.keel/config.yaml` unter `korridore`; Verletzungen geben Exit-Code 3. `/keel:kennzahlen` zeigt die Tabelle, `/keel:inbox` eine Zeile.
- **Coach** ist eine Rolle mit Web-Zugriff und als einzige Rolle mit Lesezugriff auf den Kennzahlen-Ordner. Output: Coach-Bericht mit Hypothesen-Prüfung, Umfeld-Bewertung, und höchstens drei Vorlagen mit Hypothese. Er ändert nichts. System-ADRs des Motors liest er aus dem Plugin-Verzeichnis.
- **Backlog-Port** `scripts/backlog.py` mit den sechs Befehlen aus dem Konzept und den Adaptern `markdown` (Standard) und `github` (Labels `keel:<status>`, Rang über optionale `prio:n`-Labels, sonst Alter). Anbieterwahl in `.keel/config.yaml`.
- **Kontext-Alarm** als PostToolUse-Hook für die Haupt-Session: exakte Kontextgröße aus dem Transkript, ab `budget.context_percent` des Fensters eine Anweisung als `additionalContext`, einmal pro Zehn-Prozent-Schritt.

## Folgen

- Vorlagen tragen `entschieden: <Datum>`, damit die Entscheidungsdauer messbar ist. Der Mensch setzt es beim Entscheiden.
- Die Kennzahl „Tokens pro Aufgabe“ braucht die Transkriptpfade in `events.jsonl`; sie sind erst ab dieser Version vorhanden.
- Der Kontext-Alarm ist eine Anweisung, keine Sperre. Ob der Lead ihr folgt, misst die Kennzahl `kontext_alarme` zusammen mit den Zwischenübergaben.
