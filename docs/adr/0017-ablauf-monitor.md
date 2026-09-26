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

- **`scripts/monitor.py`** startet einen kleinen HTTP-Server aus der Standardbibliothek und liefert eine Seite (`scripts/monitor.html`) ohne externe Abhängigkeiten; einzige Ausnahme ist Mermaid für gezeichnete Diagramme, siehe unten. `/keel:monitor` startet ihn losgelöst (`--ensure`), er überlebt die Session; `/keel:monitor stop` beendet ihn. Aus dem Terminal geht es direkt.
- **Autostart per Konfiguration.** Mit `monitor.autostart: true` in `.keel/config.yaml` starten die Befehle, die das System arbeiten lassen, den Monitor mit: `/keel:start`, `vorhaben`, `epic`, `tagesstart` und `briefing` über den skill-gate-Hook, dazu `keel.sh` und `keel-run.sh`. Läuft er schon, passiert nichts; belegt ein anderer Dienst oder der Monitor eines anderen Projekts den Port (`monitor.port`), startet er nicht, und die Arbeit läuft trotzdem. Standard ist `false`: niemand bekommt ungefragt einen Server.
- **Die Seite zeigt:** je Vorhaben eine Zeitleiste (Phase im Ablauf mit zuständigen Rollen, Aufgaben mit Reviews und Compliance, Abnahmenachweis, zugehörige Vorlagen, alle Rollenläufe mit Dauer, Ergebnis, blockierten Übergaben und Budgetereignissen); die laufende Rolle mit Bezug, Dauer, Werkzeugaufrufen und dem Befehl, in dem der Lead sie gerufen hat; den letzten Lauf jeder Rolle; Fälligkeiten; offene Vorhaben, Epics und Vorlagen; einen Ereignisstrom mit Befehlen, Rollenläufen, blockierten Übergaben und Ablehnungen samt Grund; alle Markdown-Dateien unter `.keel/` mit Frontmatter und gerendertem Text, Bezüge zwischen ihnen als Links; die Dokumente des Motors (Konzept, System, ADRs, Rollen, Befehle).
- **Eine Quelle.** Der Monitor nutzt `lage.py` (`build_report`, `agent_runs`), dieselbe Lage wie `/keel:hilfe`. Er führt keinen eigenen Zustand.
- **Beobachter ohne Schreibwege.** Keine Entscheidung über die Seite, kein Statuswechsel, kein Aufräumen, kein Rollenstart. Geschrieben wird nur außerhalb des Repos: Log und PID des losgelöst gestarteten Servers unter `~/.keel-metrics/<projekt>/logs/`. Vorlagen entscheidet weiter der Supervisor oder der Mensch im Briefing. Wer einen Schreibweg will, braucht einen neuen System-ADR.
- **Nur lokal.** Der Server bindet an 127.0.0.1, beantwortet nur Anfragen an localhost (Schutz gegen DNS-Rebinding) und liefert nur Markdown unter `.keel/` des Projekts und unter `docs/`, `agents/`, `skills/` des Plugins.
- **Eine Tabelle für die Ablaufregeln: `scripts/flow.py`.** Sie hält je Rolle und Anlass, welchen Status das Objekt für den Start braucht (`GATES`), welche Rollen eine harte Fälligkeit freigibt (`DUE_ROLES`), die Phasen eines Vorhabens und wer für einen Plan- oder Aufgabenstatus als Nächstes dran ist (Spiegel von `skills/vorhaben/SKILL.md`). `hooks/agent-gate.sh` liest daraus die Status- und Pflichtfeldlisten und die Fälligkeitsrollen; seine übrigen Prüfungen und alle Meldungen bleiben im Hook. Ist die Tabelle nicht lesbar, startet keine Rolle.
- **Ablaufdiagramm mit aktiv, bereit, gesperrt, ruht.** Der Monitor zeigt die Rollen in ihren Bahnen (Entscheiden, Vorhaben, Aufgabenzyklus, Prüfen und Lernen). Bereit heißt: ein Objekt erfüllt die Startbedingung aus derselben Tabelle, die der Hook prüft, und der Knoten nennt es. Gesperrt heißt: eine harte Fälligkeit gibt nur andere Rollen frei. Welche der bereiten Rollen der Lead ruft, bleibt seine Entscheidung; läuft schon eine Rolle, warten die anderen. Epic-Abnahme und Epic-Retrospektive hängen am Fortschritt des Epics und erscheinen nicht als bereit.
- **Diagramme aus den Dokumenten** zeichnet die Seite mit Mermaid, das sie beim ersten Bedarf von jsdelivr lädt. Ohne Netz bleibt der Quelltext stehen; der Rest der Seite braucht kein Netz.
- **Regressionstest für das Gate:** `tests/gate/run.py --against <ref>` schickt rund 250 Rollenstarts in vier Projektzuständen (normal, Briefing, Tagesabschluss, Audit fällig) an das Gate des Arbeitsstands und eines Git-Stands und vergleicht Antwort, Exit-Code, geparkten Bezug und Ereignisse. Jede Änderung am Gate oder an `flow.py` läuft vorher dagegen.

## Folgen

- Der Monitor sieht nur den Betrieb des Rechners, auf dem er läuft, weil die Ereignisse unter `~/.keel-metrics/` liegen.
- Er liest den Kennzahlen-Ordner, den arbeitende Rollen nicht lesen dürfen. Das ist unkritisch, weil der Mensch ihn liest, nicht eine Rolle; der Server gibt nichts davon an eine Session zurück.
- `lage.py` hat mit `build_report` und `agent_runs` eine Schnittstelle bekommen, auf die sich Hilfe und Monitor stützen; eine Änderung an der Lage wirkt in beiden.
- Eine Änderung der Startbedingungen geschieht in `flow.py` und wirkt in Gate und Monitor zugleich. Die Tabelle für „als Nächstes“ spiegelt den Vorhaben-Skill und muss mit ihm geändert werden.
- Nebenbefund beim Test: Der Doppelstart-Schutz im Gate fragte das Alter der Parkdatei zuerst mit der macOS-Syntax von `stat` ab. Unter Linux lieferte das eine andere Ausgabe, der Hook brach ab, und ein abgebrochener Hook lässt den Aufruf durch. Jetzt kommt die GNU-Syntax zuerst, macOS fällt auf seine zurück.
