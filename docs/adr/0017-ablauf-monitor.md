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

- **`scripts/monitor.py`** startet einen kleinen HTTP-Server aus der Standardbibliothek und liefert eine Seite (`scripts/monitor.html`) ohne externe Abhängigkeiten. `/keel:monitor` startet ihn losgelöst (`--ensure`), er überlebt die Session; `/keel:monitor stop` beendet ihn. Aus dem Terminal geht es direkt.
- **Autostart per Konfiguration.** Mit `monitor.autostart: true` in `.keel/config.yaml` starten die Befehle, die das System arbeiten lassen, den Monitor mit: `/keel:start`, `vorhaben`, `epic`, `tagesstart` und `briefing` über den skill-gate-Hook, dazu `keel.sh` und `keel-run.sh`. Läuft er schon, passiert nichts; belegt ein anderer Dienst oder der Monitor eines anderen Projekts den Port (`monitor.port`), startet er nicht, und die Arbeit läuft trotzdem. Standard ist `false`: niemand bekommt ungefragt einen Server.
- **Die Seite zeigt:** je Vorhaben eine Zeitleiste (Phase im Ablauf mit zuständigen Rollen, Aufgaben mit Reviews und Compliance, Abnahmenachweis, zugehörige Vorlagen, alle Rollenläufe mit Dauer, Ergebnis, blockierten Übergaben und Budgetereignissen); die laufende Rolle mit Bezug, Dauer, Werkzeugaufrufen und dem Befehl, in dem der Lead sie gerufen hat; den letzten Lauf jeder Rolle; Fälligkeiten; offene Vorhaben, Epics und Vorlagen; einen Ereignisstrom mit Befehlen, Rollenläufen, blockierten Übergaben und Ablehnungen samt Grund; alle Markdown-Dateien unter `.keel/` mit Frontmatter und gerendertem Text, Bezüge zwischen ihnen als Links; die Dokumente des Motors (Konzept, System, ADRs, Rollen, Befehle).
- **Eine Quelle.** Der Monitor nutzt `lage.py` (`build_report`, `agent_runs`), dieselbe Lage wie `/keel:hilfe`. Er führt keinen eigenen Zustand.
- **Beobachter ohne Schreibwege.** Keine Entscheidung über die Seite, kein Statuswechsel, kein Aufräumen, kein Rollenstart. Geschrieben wird nur außerhalb des Repos: Log und PID des losgelöst gestarteten Servers unter `~/.keel-metrics/<projekt>/logs/`. Vorlagen entscheidet weiter der Supervisor oder der Mensch im Briefing. Wer einen Schreibweg will, braucht einen neuen System-ADR.
- **Nur lokal.** Der Server bindet an 127.0.0.1, beantwortet nur Anfragen an localhost (Schutz gegen DNS-Rebinding) und liefert nur Markdown unter `.keel/` des Projekts und unter `docs/`, `agents/`, `skills/` des Plugins.
- **„Als Nächstes laut Ablauf“ statt Vorhersage.** Welche Rolle der Lead ruft, entscheidet er im Fall. Für einen Plan- oder Aufgabenstatus legt `skills/vorhaben/SKILL.md` aber fest, wer als Nächstes dran ist (`geplant` → Tester, `tests-bereit` → Entwickler, `abnahme-bereit` → PO …). Der Monitor zeigt diese Regel aus einer Tabelle in `monitor.py`, die den Skill spiegelt; ändert sich der Ablauf im Skill, muss die Tabelle mit. Ob eine Rolle starten *darf* (`agent-gate.sh`), als „bereit/gesperrt“ anzuzeigen, verlangt eine gemeinsame Regeltabelle für Gate und Monitor und ist ein späterer Schritt, ebenso gerenderte Diagramme.

## Folgen

- Der Monitor sieht nur den Betrieb des Rechners, auf dem er läuft, weil die Ereignisse unter `~/.keel-metrics/` liegen.
- Er liest den Kennzahlen-Ordner, den arbeitende Rollen nicht lesen dürfen. Das ist unkritisch, weil der Mensch ihn liest, nicht eine Rolle; der Server gibt nichts davon an eine Session zurück.
- `lage.py` hat mit `build_report` und `agent_runs` eine Schnittstelle bekommen, auf die sich Hilfe und Monitor stützen; eine Änderung an der Lage wirkt in beiden.
