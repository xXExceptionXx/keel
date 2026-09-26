---
nummer: 0017
titel: Ablauf-Monitor als lokale Webseite, Beobachter ohne Schreibwege
status: Accepted
datum: 2026-09-26
entscheider: Ich
supersedes:
hypothese: Mit dem Monitor neben der Arbeit sieht der Mensch jederzeit, welche Rolle an welcher Aufgabe arbeitet und warum etwas steht, ohne eine Hilfe-Session zu öffnen; /keel:hilfe wird seltener für „was läuft gerade“ aufgerufen und öfter für echte Fragen, und Übergaben werden gelesen statt nur geprüft
---

# 0017: Ablauf-Monitor als lokale Webseite, Beobachter ohne Schreibwege

## Kontext

keel arbeitet still. Wer gerade aktiv ist, zeigen Zustandsdateien im Kennzahlen-Ordner; was geschah, steht in `events.jsonl`; der Stand jedes Vorhabens steckt im Frontmatter der Dateien unter `.keel/work/`. `/keel:hilfe` macht das auf Abruf sichtbar, aber nur als Momentaufnahme im Gespräch. Die Übergaben selbst liest kaum jemand, obwohl sie genau erklären, was das System getan hat und warum.

## Entscheidung

- **`scripts/monitor.py`** startet einen kleinen HTTP-Server aus der Standardbibliothek und liefert eine Seite (`scripts/monitor.html`) ohne externe Abhängigkeiten. `/keel:monitor` startet ihn aus einer Session, aus dem Terminal geht es direkt.
- **Die Seite zeigt:** die laufende Rolle mit Bezug, Dauer, Werkzeugaufrufen und dem Befehl, in dem der Lead sie gerufen hat; den letzten Lauf jeder Rolle; Fälligkeiten; offene Vorhaben, Epics und Vorlagen; einen Ereignisstrom mit Befehlen, Rollenläufen, blockierten Übergaben und Ablehnungen samt Grund; alle Markdown-Dateien unter `.keel/` mit Frontmatter und gerendertem Text, Bezüge zwischen ihnen als Links; die Dokumente des Motors (Konzept, System, ADRs, Rollen, Befehle).
- **Eine Quelle.** Der Monitor nutzt `lage.py` (`build_report`, `agent_runs`), dieselbe Lage wie `/keel:hilfe`. Er führt keinen eigenen Zustand.
- **Beobachter ohne Schreibwege.** Keine Entscheidung über die Seite, kein Statuswechsel, kein Aufräumen, kein Rollenstart. Vorlagen entscheidet weiter der Supervisor oder der Mensch im Briefing. Wer einen Schreibweg will, braucht einen neuen System-ADR.
- **Nur lokal.** Der Server bindet an 127.0.0.1, beantwortet nur Anfragen an localhost (Schutz gegen DNS-Rebinding) und liefert nur Markdown unter `.keel/` des Projekts und unter `docs/`, `agents/`, `skills/` des Plugins.
- **„Wer kommt als Nächstes“ bleibt offen.** Welche Rolle der Lead ruft, entscheidet er im Fall. Ob eine Rolle starten *darf*, folgt aus den Status in `agent-gate.sh`; das als „bereit/gesperrt“ anzuzeigen, verlangt eine gemeinsame Regeltabelle für Gate und Monitor und ist ein späterer Schritt, ebenso die Zeitleiste je Vorhaben und gerenderte Diagramme.

## Folgen

- Der Monitor sieht nur den Betrieb des Rechners, auf dem er läuft, weil die Ereignisse unter `~/.keel-metrics/` liegen.
- Er liest den Kennzahlen-Ordner, den arbeitende Rollen nicht lesen dürfen. Das ist unkritisch, weil der Mensch ihn liest, nicht eine Rolle; der Server gibt nichts davon an eine Session zurück.
- `lage.py` hat mit `build_report` und `agent_runs` eine Schnittstelle bekommen, auf die sich Hilfe und Monitor stützen; eine Änderung an der Lage wirkt in beiden.
