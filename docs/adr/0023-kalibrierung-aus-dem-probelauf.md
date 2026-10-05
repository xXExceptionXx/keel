---
nummer: 0023
titel: Einwände nur bei Abweichung, Briefings als Läufe des Supervisors, absolute Kontextgrenze
status: Accepted
datum: 2026-10-05
entscheider: Ich
supersedes:
hypothese: Im nächsten Probelauf steht der Korridor der Einwände ohne Abweichung auf n/a statt auf verletzt; ein Modellwechsel des Supervisors ist nach höchstens zehn Briefings bewertbar; der Kontext-Alarm kommt beim Lead bei 100k Tokens, unabhängig vom Modell
---

# 0023: Einwände nur bei Abweichung, Briefings als Läufe des Supervisors, absolute Kontextgrenze

## Kontext

Der Probelauf vom 2026-10-01 hat drei Punkte am Motor offen gelassen (`docs/kern-befunde.md`, P1 bis P3). Der Korridor `einwaende_supervisor: 1-10` meldete eine Verletzung, obwohl der Mensch nie gegen die Empfehlung des Supervisors entschieden hatte; er erzeugte Druck zu erfundenem Widerspruch. Briefings laufen in der Hauptsitzung und zählten deshalb nicht für die zehn Läufe, nach denen ein Modellwechsel bewertet wird (System-ADR 0015); nach zehn Tagen standen zwei von zehn. `budget.context_window: 200000` beschrieb ein Fenster, das die aktuellen Modelle (1M) längst überschreiten, gemeint war eine absolute Grenze für Kontextpflege.

## Entscheidung

**P1.** Die Vorlage trägt `empfehlung` (gesetzt vom Supervisor im Briefing vor der Entscheidung) und `abweichung: ja|nein` (gesetzt nach der Entscheidung). Die Kennzahl `einwaende_bei_abweichung_prozent` ist der Anteil der Abweichungen, zu denen ein `## Einwand des Supervisors` im ADR steht; ohne Abweichung ist sie n/a. Korridor 50–100. `einwaende_supervisor` entfällt.

**P2.** Das Ende eines geprüften Briefings (`briefing_geprueft`, `briefing_protokoll_offen`) trägt das Modell der Session und zählt in `models.py` als Lauf des Supervisors.

**P3.** `budget.context_tokens: 100000` ersetzt `budget.context_window` und `budget.context_percent`. Der Kontext-Alarm kommt ab dieser Zahl und erneut je weitere zehn Prozent davon.

## Verworfen

- P1: Untergrenze 0 (das Warnsignal für einen Supervisor, der nach dem Mund redet, entfiele); nichts ändern.
- P2: eine eigene, niedrigere Schwelle für den Supervisor (zählt weiter an der falschen Stelle).
- P3: das Fenster auf 1M heben (der Alarm käme erst bei 500k, Kontextpflege zu spät).

## Folgen

- Keine Migration: Das Plugin läuft in keinem Projekt; ein neues Beispielprojekt startet mit den neuen Schlüsseln.
- Briefing-Skill und Coach-Rolle beschreiben die neuen Felder.
