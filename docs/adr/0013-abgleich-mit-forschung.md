---
nummer: 0013
titel: Abgleich mit MAST-Taxonomie und Harness-Befunden, fünf Ergänzungen
status: Accepted
datum: 2026-09-22
entscheider: Ich
supersedes:
hypothese: Kein Stub und kein übersprungener Test erreicht mehr einen Review; die Stichprobe des Auditors weicht in weniger als 10 % der Fälle vom Reviewer ab; der Coach schlägt innerhalb von zwei Läufen mindestens eine Schutzmaßnahme zum Rückbau vor
---

# 0013: Abgleich mit MAST-Taxonomie und Harness-Befunden

## Kontext

Prüfung des Standes 0.9 gegen Cemri et al. (14 Fehlermodi), Anthropics Harness-Berichte (C-Compiler, Effective harnesses, Harness design, Managed Agents), Cognition („Don't build multi-agents“) und Cursor. Ergebnis: 8 Fehlermodi abgedeckt, 6 teilweise, keiner offen. Die Teilabdeckungen liegen beim Inter-Agent-Alignment, also dort, wo keel Kontext bewusst kappt.

## Entscheidung

Fünf Ergänzungen, alle klein:

1. **Stubs blockieren.** Der Compliance-Scan blockiert `TODO`, `not implemented` und übersprungene Tests im Diff, wie Secrets. Anthropic: „feature stubs escaped notice“.
2. **Credentials sind unlesbar.** Der Guard lehnt `env`, `printenv`, `gh auth token`, Token-Variablen und das Lesen von `.env`, `.netrc`, Schlüsseln und `.claude.json` ab. Anthropic Managed Agents: der Harness kennt keine Credentials.
3. **Entscheidungen wandern zwischen Aufgaben.** Jede Aufgaben-Datei hat `## Entscheidungen`; der Entwickler schreibt Namen, Formen und Helfer hinein und liest die der vorigen Aufgaben, der Reviewer prüft gegen sie. Cognition: Handlungen tragen implizite Entscheidungen, widersprüchliche Entscheidungen tragen schlechte Ergebnisse.
4. **Stichprobe gegen Reviewer-Nachsicht.** Der Auditor prüft täglich eine bestandene Aufgabe selbst; Abweichungen zählt der Coach. Anthropic: Modelle loben KI-Output auch bei mittelmäßiger Qualität.
5. **Rückbau ist ein Vorschlag wie Einbau.** Der Coach zählt Auslösungen je Schutzmaßnahme und schlägt Abschaltung vor, wenn eine über zwei Läufe still bleibt, bei Modellwechsel für alle. Anthropic: Schutz für ein altes Modell wird beim neuen totes Gewicht.

Nicht übernommen, bewusst: Drift-Befunde automatisch als Reparatur ohne PO (OpenAI, Entropie-Abbau); bleibt Backlog-Vorschlag, bis die Wochenrunde zeigt, dass Befunde versanden.

## Bekannte Preise, bewusst gezahlt

- Das Briefing-Gate sperrt alle Rollen, sobald eine Supervisor-Entscheidung unvorgelegt ist. Ein unbeaufsichtigter Nachtlauf endet damit nach der ersten Supervisor-Entscheidung. Entscheidung von xXExceptionXx: Vorlegen vor Weiterbauen.
- Kontext wird an jeder Grenze gekappt, Nacharbeit läuft immer mit frischem Entwickler. Preis: Neu-Exploration je Runde. Ergänzung 3 mildert das, hebt es nicht auf.
- Jede Klärung kostet mehrere Rollenläufe; der erste Lauf brauchte 13 für drei Aufgaben. Der Preis ist Nachvollziehbarkeit und Unabhängigkeit der Tests.
