---
nummer: 0022
titel: Ein Python-Prozess je Hook-Ereignis, Laufzeitzustand an einer Stelle
status: Accepted
datum: 2026-10-05
entscheider: Ich
supersedes:
hypothese: In vier Wochen Betrieb gibt es kein hook_error ohne benannte Ursache, kein Gate lässt wegen eines internen Fehlers durch, keine Rolle wird durch eine liegengebliebene Startmarke gesperrt, kein Werkzeugaufruf geht im Zähler verloren, und der Median eines Werkzeugaufrufs über alle Hooks bleibt unter 150 ms
---

# 0022: Ein Python-Prozess je Hook-Ereignis, Laufzeitzustand an einer Stelle

## Kontext

Schritt M2 aus `docs/kern-architektur.md`, Arbeitspaket 4. Die elf Hooks waren Bash-Skripte mit rund 1100 Zeilen. Sie trugen die Ein- und Austrittsregeln aller Rollen selbst, lasen jedes Feld des Payloads mit einem eigenen `jq` und riefen für jede Frontmatter-Prüfung `frontmatter.py` auf. Ein `Edit` einer Rolle startete 14 `jq`- und 5 `python3`-Prozesse. Der Fehlervertrag aus System-ADR 0019 war in `hooks/lib.sh` mit `trap` nachgebaut und hielt nur, solange jede neue Prüfung ihn von Hand richtig benutzte.

Offene Befunde aus `docs/kern-befunde.md`, alle in den Hooks: U1 bis U3 (Pfade in den Schutzregeln nicht normalisiert), U4 (Lücken im Guard), N1 (Werkzeugzähler ohne Sperre, 20 parallele Aufrufe ergaben 16), N2 (`pending-<rolle>` nicht atomar, eine abgelehnte Freigabe sperrte die Rolle zehn Minuten).

Laut Hook-Doku von Claude Code (2.1.285) laufen alle passenden Hooks eines Ereignisses parallel. Nur Exit 2 blockiert, ein Timeout oder ein fehlendes Programm (Exit 127) lässt durch. `SubagentStart` liefert keine `tool_use_id` des Agent-Aufrufs.

## Entscheidung

**Ein Eintrag je Ereignis.** `hooks/hooks.json` ruft für jedes Ereignis `bin/keel hook <ereignis>` auf. Der Dispatcher in `lib/keel/interfaces/hooks.py` liest den Payload einmal und führt alle registrierten Schritte des Ereignisses nacheinander aus: `PreToolUse` guard (Bash), agent-gate (Agent), skill-gate (Skill), tool-gate und Protokoll, `PostToolUse` Protokoll und Kontext-Alarm, `SubagentStart` agent-start, `SubagentStop` agent-stop, `Stop` Protokoll und briefing-stop, `SessionStart` Protokoll und session-gate, `UserPromptSubmit` Protokoll und skill-gate. `SessionEnd` und `Notification` kommen neu ins Protokoll (Lebenszeichen Ebene 1). Jeder Schritt läuft, auch nach einer Ablehnung, damit Zähler und Protokoll gleich bleiben wie mit parallelen Hooks. Die erste Ablehnung gewinnt, zusätzlicher Kontext wird verbunden. `hooks/<schritt>.sh` bleibt als Einzeiler (`bin/keel hook --only <schritt>`), damit Tests einen Schritt einzeln ansprechen.

**Der Fehlervertrag an einer Stelle.** Ein Gate, das nicht prüfen kann (`CannotCheck` oder jede andere Ausnahme), endet mit Exit 2 und Meldung. Beim Ende einer Rolle zieht der dritte interne Fehler desselben Agenten die Notbremse aus System-ADR 0019. Ein Beobachter blockiert nie; sein Fehler wird `hook_error` mit dem Namen des Schritts. Fehlt `python3`, entscheidet `bin/keel` in Bash: Der Guard schließt für jeden Bash-Aufruf, die übrigen Gates für Aufrufe mit `keel:` im Payload, Beobachter lassen durch. `jq` brauchen die Hooks nicht mehr.

**Regeln in Python, eins zu eins.** Die Schritte liegen unter `lib/keel/services/hooks/`, je Rolle eine Funktion mit den bisherigen Meldungen. Die Startbedingungen stehen in `lib/keel/domain/flow.py`; `scripts/flow.py shell` und das `eval` im Gate entfallen. `due.py`, `briefing_needed.py`, `compliance_scan.py`, `review.py`, `pflege.py`, `models.py`, `wiedervorlage.py` und `gate.sh` laufen bis M3/M4 als Unterprozess (`services/hooks/legacy.py`). Frontmatter, Konfiguration und ADR-Stand laufen im Prozess. Tabellen statt Funktionen folgen in M3.

**Laufzeitzustand an einer Stelle.** Nur `lib/keel/store/runtime.py` kennt die Ablage unter `state/`: `agents/<id>.json` (Rolle, Bezug, Start, Zähler, langsam, interne Fehler) mit `agents/<id>.adr.json`, `pending/<rolle>.json` mit `pending/<rolle>.adr.json`, `sessions/<sid>.json` (Hilfe-Session, Stufe des Kontext-Alarms) mit `sessions/<sid>.briefing.json`, `activities/<name>-<pid>.json`. Die Notbremse `kern-gesperrt` bleibt eine Textdatei, die der Mensch löscht. `lage.py`, der Monitor und `keel doctor` lesen über die API. Keine Migration, das Plugin läuft in keinem Projekt.

**Befunde.**
- N1: Der Zähler wird unter einer Sperre gelesen, erhöht und geschrieben. Ein unlesbarer Zähler blockiert.
- N2: Eine Startmarke wird exklusiv angelegt. Sie gilt als verwaist, wenn kein Agent dieser Rolle läuft und sie älter als 30 Sekunden ist. Dann wird sie ersetzt und als `pending_verwaist` protokolliert, statt die Rolle zehn Minuten zu sperren. Zwei gleichzeitige Freigaben derselben Rolle lassen genau eine durch.
- U1, U3: Testschutz und Budget-Ausnahme vergleichen Pfade nach `realpath` relativ zum Projekt.
- U2: Die Sperre des Kennzahlen-Ordners erkennt auch `~/.keel-metrics`, `$KEEL_METRICS_DIR` und `$HOME/…`.
- U4: Der Guard kennt Force-Push per Refspec, `rm` mit langen Optionen oder `"$HOME"`, `find -delete` außerhalb des Arbeitsverzeichnisses, `cd /` mit folgendem rekursivem `rm`. Ein Remote-Branch darf nur gelöscht werden, wenn er in der Basis enthalten ist.
- Der Guard prüft jedes Muster je Befehlsteil (zwischen `;`, `&&`, `||`, `|`) und bleibt so auch bei sehr langen Befehlen linear.

**Lebenszeichen Ebene 2.** Prüftor und Compliance-Scan melden sich mit `Runtime.activity()` an (Marker mit Prozess-ID, Start und Bezug). Ein Marker, dessen Prozess nicht mehr lebt, ist verwaist; `keel doctor` meldet ihn, `lage.py --clean` räumt ihn auf. Die Anzeige im Monitor gehört zu M6.

**Bytecode.** Ist das Schreiben von Bytecode abgeschaltet (`PYTHONDONTWRITEBYTECODE`), legt `bin/keel hook` den Cache in einen eigenen Ordner unter dem Kennzahlen-Ordner, nie neben die Quellen des Plugins.

## Gemessen

`tests/perf/hooks.py`, Median aus 20 Läufen je Werkzeugaufruf (`PreToolUse` und `PostToolUse`), macOS, Python 3.9:

| Szenario | 0.16.0 parallel | 0.16.0 Summe | 0.17.0 |
| --- | --- | --- | --- |
| `Edit` einer Rolle | 315 ms | 622 ms | 102 ms |
| `Bash` des Leads | 178 ms | 317 ms | 99 ms |

„Parallel“ ist die Wartezeit, „Summe“ die Rechenzeit aller Hooks. Mit einem Prozess je Ereignis fallen beide zusammen.

## Verworfen

- **Den Guard in Bash lassen.** `kern-architektur.md` hätte es erlaubt. Dann wäre `PreToolUse` auf `Bash` zwei Prozesse geblieben, und die U4-Muster wären in Python besser zu testen.
- **Die Regeln gleich als Tabellen schreiben.** Der Vergleich gegen den vorigen Stand wäre schwerer zu lesen gewesen, weil sich Ort und Form gleichzeitig geändert hätten.
- **Verwaiste Startmarke über die `tool_use_id`.** `SubagentStart` liefert sie nicht.
- **Die Prozess-ID der Session für „abgebrochen“.** Sie ist in der Hook-Doku nicht beschrieben; Ebene 1 protokolliert vorerst nur `SessionEnd` und `Notification`.
- **Alle Hilfsskripte in den Prozess holen.** Das hätte M3 und M4 vorweggenommen. Der heiße Pfad (Guard, Werkzeug-Gate, Protokoll, Kontext-Alarm) läuft ohne Unterprozess; die übrigen Gates laufen selten.

## Folgen

- Eine neue Prüfung kann den Fehlervertrag nicht mehr versehentlich brechen: Sie wirft oder gibt ein Ergebnis zurück.
- Vertragstests lesen und setzen den Laufzeitzustand nur noch über `harness.py` (`seed_agent`, `agent_state`, `pending_of`, `state`), nicht über Dateinamen.
- `tests/gate/hooks.py` vergleicht agent-stop, tool-gate, skill-gate und guard mit dem vorigen Stand. Gewollte Abweichungen stehen dort mit Grund. `tests/perf/hooks.py` misst die Latenz.
- `scripts/jsonl.py`, `hooks/lib.sh` und `flow.py shell` sind entfernt.
- Der Schutz der Testdateien gilt nur für die Datei-Werkzeuge. Schreibzugriffe über Bash bleiben eine dokumentierte Lücke, ebenso wie die übrigen Leitplanken des Guards.
