---
nummer: 0019
titel: Fehlervertrag für Kern und Hooks, Gates schließen bei Fehlern, Beobachter laufen weiter
status: Accepted
datum: 2026-10-01
entscheider: Ich
supersedes:
hypothese: Kein Rollenstart und kein Rollenende geht mehr ungeprüft durch, weil ein Hilfsskript abstürzt, ein Werkzeug fehlt oder ein Feld leer ist; die Vertragstests unter tests/contract belegen das für jeden bekannten Fall; in vier Wochen Betrieb tauchen hook_error-Ereignisse auf, aber kein Durchlass, der sich im Nachhinein als Fehler im Gate herausstellt
---

# 0019: Fehlervertrag für Kern und Hooks, Gates schließen bei Fehlern, Beobachter laufen weiter

## Kontext

Eine Prüfung des Kerns (`docs/kern-befunde.md`) hat gezeigt, dass mehrere Gates bei Fehlern still durchlassen. Der Grund liegt in Claude Code: Ein Hook blockiert nur mit Exit-Code 2 oder einer ausdrücklichen Ablehnung. Jeder andere Exit-Code ist ein „nicht blockierender Fehler“, und der Aufruf geht weiter. Ein Hook, der in sein Timeout läuft, wird abgebrochen und lässt ebenfalls durch.

Im Bestand hieß das:
- Ohne `jq` oder mit kaputtem Payload starteten Rollen ungeprüft.
- `agent-stop.sh` brach bei einem fehlenden Feld mit Exit 1 ab, und das Ende des Rollenlaufs galt als geprüft.
- Ein abstürzender Compliance-Scan fiel durch alle Fälle, ein Git-Fehler im Scan ergab „frei“.
- Ein Absturz von `due.py` oder `briefing_needed.py` endete mit Exit 1, also derselben Antwort wie „etwas ist fällig“ oder „Briefing nötig“. Je nach Aufrufer öffnete oder schloss das ein Tor.
- Das Prüftor lief ohne Zeitgrenze im Stop-Hook.

Jedes Skript hatte seine eigene Bedeutung für Exit-Codes, und kein Hook konnte „Regel verletzt“ von „Programm kaputt“ unterscheiden.

## Entscheidung

**Exit-Vertrag für Skripte des Kerns.** 0 heißt nein oder erfolgreich, 1 heißt ja oder fachlich abgelehnt, 2 heißt: konnte nicht prüfen (Bedienfehler, Werkzeugfehler, interner Fehler). Skripte, deren Ergebnis ein Gate auswertet, fangen jede Ausnahme und enden dann mit 2: `due.py`, `briefing_needed.py`, `compliance_scan.py` (dort bleiben 0, 3, 4, 5 die Ergebnisklassen). Aufrufer werten jeden Code ausdrücklich aus, ein unbekannter Code zählt wie 2. Ein Exit 1 ohne lesbare Antwort zählt ebenfalls wie 2, weil ein Absturz vor der eigenen Fehlerbehandlung des Skripts mit 1 endet.

**Gates schließen bei Fehlern.** `guard.sh`, `agent-gate.sh`, `tool-gate.sh`, `skill-gate.sh` und `agent-stop.sh` rufen `keel_gate_init` aus `hooks/lib.sh` auf. Ein Gate endet nur auf vier Wegen: `keel_ok`, `deny`, `block_stop` oder `gate_fail`. Jedes andere Ende, ob durch `set -e`, eine ungebundene Variable oder ein fehlendes Werkzeug, fängt eine EXIT-Falle und macht daraus Exit 2 mit einer deutschen Meldung auf stderr. `deny` und `block_stop` geben die Entscheidung aus, bevor sie protokolliert wird, damit ein scheiterndes Protokoll keine Ablehnung in einen Durchlass verwandelt. Fehlt `jq` oder `python3`, blockieren die Gates; Aufrufe, die keel nicht betreffen (kein `keel:` im Payload), lassen alle Gates außer `guard.sh` durch, damit ein fehlendes Werkzeug nicht jede Session lahmlegt.

**Beobachter laufen weiter.** `log.sh`, `context-alarm.sh`, `agent-start.sh` und `session-gate.sh` rufen `keel_observer_init` auf. Ein Fehler wird als Ereignis `hook_error` protokolliert, der Aufruf geht weiter.

**Fehlende Daten werden benannt, nicht übergangen.** Wo ein Gate ein Feld braucht, prüft es ausdrücklich und lehnt mit einer Meldung ab, die Feld und Datei nennt, statt über einen Abbruch zu stolpern.

**Internes Timeout kürzer als das Hook-Timeout.** Das Prüftor läuft über `scripts/timeout.py` mit `test.timeout` (Standard 480 Sekunden, höchstens 540), der Stop-Hook hat in `hooks/hooks.json` ein Timeout von 600 Sekunden. So beendet immer das interne Timeout die Suite und das Gate entscheidet, nicht der Abbruch durch Claude Code. `timeout.py` beendet die ganze Prozessgruppe, nach einer Gnadenfrist immer mit SIGKILL, damit keine Test-Worker überleben.

**Notbremse für das Rollenende.** Ein Stop-Hook, der intern scheitert, blockiert das Ende des Rollenlaufs. Die Rolle kann den Kern aber nicht reparieren und würde es endlos erneut versuchen. Nach dem dritten internen Fehler für denselben Agenten lässt `agent-stop.sh` das Ende deshalb durch, protokolliert `hook_error` und legt `kern-gesperrt` im Laufzeit-Ordner an. Solange die Datei existiert, lehnt `agent-gate.sh` jede Rolle ab. Der Mensch behebt die Ursache und löscht die Datei. So bleibt das System als Ganzes geschlossen, ohne dass eine Rolle Tokens verbrennt.

**Gemeinsame Dateien werden atomar geschrieben.** Ereignisse und Hook-Protokoll schreibt `scripts/jsonl.py` mit einem einzigen Schreibvorgang unter einer Sperre.

**Belegt durch Vertragstests.** `tests/contract/` prüft Hooks und Skripte von außen: Payload oder Kommandozeile hinein, Exit-Code, Antwort und Ereignisse heraus. Eine CI führt sie auf einem Linux-Runner mit Python 3.9 aus. macOS mit der System-Python 3.9 und Bash 3.2 prüft der pre-push-Hook unter `.githooks/` lokal; macOS-Runner kosten auf GitHub das Zehnfache an Minuten und sind seit 2026-10-02 aus der CI genommen.

## Folgen

- Fälle, die früher still durchgingen, blockieren jetzt, mit einer Meldung, die sagt, was fehlt. Ein kaputtes Hilfsskript sperrt Rollen, bis es repariert ist. Das ist gewollt: Ein Gate, das bei Fehlern öffnet, erzeugt Vertrauen, das nicht gedeckt ist.
- Ohne `jq` ist jeder Bash-Aufruf gesperrt, weil `guard.sh` den Befehl nicht lesen kann. `jq` ist damit eine harte Voraussetzung; macOS bringt es ab Version 15 mit, sonst kommt es aus Homebrew oder der Paketverwaltung.
- Ein Wert im Frontmatter, der mit `#` beginnt (etwa `pr: #12`), gilt jetzt als Kommentar und damit als leer, wie in YAML. Solche Werte gehören in Anführungszeichen; `frontmatter.py set` schreibt sie so.
- Die Notbremse beendet einen Rollenlauf ungeprüft. Das ist der Preis dafür, dass eine Rolle nicht endlos an einem Kernfehler hängt; danach arbeitet keine Rolle mehr, bis der Mensch eingreift.
- Bekanntes Rest-Risiko: Die übrigen Gates laufen mit dem Standard-Timeout von Claude Code. Startet `agent-gate.sh` auf einem sehr großen Repository `due.py` mit Git-Abfragen, die länger dauern, wird der Hook abgebrochen und lässt durch. Behoben wird das mit dem schnelleren Dispatcher im Umbau (M2).
- Unberührte Vorlagen, deren Pflichtfelder nur einen Kommentar enthalten, gelten jetzt als leer und scheitern an `--nonempty`.
- Das Hook-Protokoll enthält keine Werkzeugantworten und Dateiinhalte mehr, nur noch, was Monitor und Coach lesen.
- Jedes Protokoll und jedes Ereignis kostet einen Python-Start. Die Leistung der Hooks ist Thema des Umbaus (Schritt M2 in `docs/kern-architektur.md`), dort wird aus vielen Prozessen je Ereignis einer.
- Dieser Vertrag ist die Grundlage für den Umbau des Kerns: Der künftige Hook-Dispatcher setzt dieselbe Unterscheidung zwischen Gate und Beobachter an einer Stelle um.
