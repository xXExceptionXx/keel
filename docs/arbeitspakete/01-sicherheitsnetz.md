# Arbeitspaket 1: Sicherheitsnetz für den Kern

2026-10-01 · Schritt M0 aus `docs/kern-architektur.md`. Grundlage: `docs/kern-befunde.md`. Zum Planen im Plan-Modus, dann Umsetzung auf einem eigenen Branch.

## Ziel

Gates, die bei Fehlern still durchlassen, werden dicht. Zwei aktive Fehler auf `main` werden behoben. Das Protokoll wird verlässlich, damit die geplanten Messungen auf sauberen Daten beruhen. Jede Korrektur bekommt einen Test mit festem Sollwert, und eine CI führt alle Tests aus.

Das Paket baut den Kern **nicht** um. Es repariert im Bestand, damit der Umbau (M1, M2) auf einem sicheren Stand beginnt.

## Warum zuerst

- Ein Gate, das bei einem Fehler durchlässt, ist schlimmer als keins: Es erzeugt Vertrauen, das nicht gedeckt ist. Heute reicht ein fehlendes `jq`, ein kaputter Payload oder ein Absturz des Compliance-Scans.
- Die Review-Schwelle aus System-ADR 0018 ist seit dem Merge von PR #3 aktiv und kann im falschen Fall `nacharbeit` statt `vorlage` liefern.
- Alle Konzepte (Kontext, Beschleunigung, Kern) beginnen mit einer Messung. Ein Protokoll mit ineinander geschriebenen Zeilen und ein Kontext-Alarm, der nie feuert, verfälschen sie.

## Umfang

Nummern wie in `docs/kern-befunde.md`.

### A. Aktive Fehler in der Review-Schwelle

| Nr. | Was | Fundstelle |
| --- | --- | --- |
| F4 | Trend ausdrücklich statt Tupel-Vergleich: „Befunde sinken“ nur, wenn keine Kategorie steigt und mindestens eine sinkt. Umgesetzt wurde nach Abstimmung: lexikografisch kleiner und die Summe aus blockierend und wichtig steigt nicht (ADR 0018 ergänzt). | `scripts/review.py:182` |
| F2 | Leeres Feld (`anmerkung:`) darf nicht abstürzen. | `scripts/review.py:131`, Ursache in `scripts/frontmatter.py` |

### B. Gates schließen bei Fehlern

| Nr. | Was | Fundstelle |
| --- | --- | --- |
| S1 | `jq` und `python3` am Anfang jedes Gates prüfen, sonst Exit 2. | `hooks/lib.sh`, alle Gates |
| S2, S3 | `trap … exit 2` auf `ERR` in jedem Gate. Fehlende Felder in `agent-stop.sh` ausdrücklich behandeln statt über `set -e` abzubrechen. | `hooks/agent-gate.sh`, `hooks/agent-stop.sh:42,45,130,158,246`, `hooks/tool-gate.sh`, `hooks/skill-gate.sh` |
| S4 | Auffangfall im `case` des Compliance-Blocks: Jeder unbekannte Exit-Code blockiert. | `hooks/agent-stop.sh:235` |
| S5 | Compliance-Scan prüft die Exit-Codes von Git und meldet Fehler mit Exit 2. | `scripts/compliance_scan.py:66` |
| S6 | Ungetrackte Dateien mit `git ls-files -z` lesen, Dateinamen mit Umlaut und Leerzeichen werden geprüft. | `scripts/compliance_scan.py:83,89` |
| S7 | Einheitlicher Exit-Vertrag für `due.py` und `briefing_needed.py`: 0 nein, 1 ja, 2 interner Fehler. Alle aufrufenden Hooks schließen bei 2. `due.py` übersteht Ereigniszeilen ohne `ts`. | `scripts/due.py:92`, `scripts/briefing_needed.py:17`, `hooks/agent-gate.sh:36`, `hooks/session-gate.sh` |
| S8 | Ausdrückliches `timeout` für den SubagentStop-Hook in `hooks.json`, eigenes Timeout in `gate.sh`, bei Abbruch blockieren. | `hooks/hooks.json`, `scripts/gate.sh`, `hooks/agent-stop.sh:225` |

Beobachter (`log.sh`, `context-alarm.sh`, `agent-start.sh`) dürfen bei Fehlern weiterlaufen lassen, sollen den Fehler aber protokollieren.

### C. Verlässliche Daten

| Nr. | Was | Fundstelle |
| --- | --- | --- |
| F1 | Frontmatter: Beim Lesen JSON-maskierte Werte mit `json.loads` entmaskieren, damit Lesen und Schreiben sich nicht gegenseitig beschädigen. | `scripts/frontmatter.py` (`_scalar`, `_quote`) |
| F3 | Kontext-Alarm liest das Transkript zeilenweise tolerant (`jq -R 'fromjson?'` oder Python), statt mitten in einer Zeile abzuschneiden. | `hooks/context-alarm.sh:14` |
| N5 | Protokoll atomar: eine Zeile mit einem einzigen `write` auf `O_APPEND` unter `flock`. Payload auf die nötigen Felder kürzen, keine vollständige `tool_response` mehr. | `hooks/log.sh:11` |
| N3 | Feste Pfade `/tmp/keel-gate-err` und `/tmp/keel-stop-err` durch `mktemp` ersetzen. Klein, betrifft dieselben Zeilen wie B. | `hooks/*.sh` |

### D. Tests und CI

- Ein neuer Testordner, zum Beispiel `tests/contract/`, mit **Vertragstests**: Payload oder Kommandozeile hinein, Antwort, Exit-Code und Ereignisse heraus, gegen feste Sollwerte. Nicht gegen eine ältere Version wie `tests/gate/`.
- Tests von außen, nicht gegen interne Funktionen. Sie sollen den Umbau in M1 und M2 unverändert überstehen und dort als Sicherung dienen.
- Mindestens je Befund ein Test, der ohne die Korrektur fehlschlägt. Fehlerfälle ausdrücklich: fehlendes `jq` (über `PATH`), kaputter Payload, fehlende Datei, fehlendes Feld, Absturz eines aufgerufenen Skripts.
- Round-Trip-Test für Frontmatter mit Anführungszeichen, Doppelpunkten, `#` und leeren Werten.
- Parallelitätstest für das Protokoll: viele gleichzeitige Aufrufe, jede Zeile ist gültiges JSON.
- Eine CI mit GitHub Actions auf macOS und Linux, Python 3.9, die `tests/contract/` und `tests/gate/` ausführt.

## Nicht im Umfang

- Umbau der Struktur (Paket, Dispatcher, `domain`): M1 und M2.
- Umgehbare Schutzregeln U1 bis U4: Sie brauchen normalisierte Pfade und eine Entscheidung, was Leitplanke und was Grenze ist. Das gehört in M2.
- Gleichzeitige Zugriffe N1, N2, N4, N6 und die Projektschlüssel: brauchen `store/runtime.py` und `store/paths.py` aus M1.
- Backlog-Verlust F5, Routing F6, Konfiguration F7, Robustheit der Berichte F8, Zeitzonen F9: Sie verschwinden strukturell mit M1.
- Leistung der Hooks: M2.

Wenn beim Planen auffällt, dass einer dieser Punkte für ein Gate dieses Pakets unverzichtbar ist, wird er hereingeholt und im Plan begründet.

## Abnahme

- Alle Befunde aus A bis C sind behoben, je mit einem Test, der ohne die Korrektur rot war.
- Ohne `jq` im `PATH` lehnt jedes Gate mit Exit 2 und verständlicher Meldung ab.
- Ein kaputter Payload, eine fehlende Datei oder ein Absturz eines aufgerufenen Skripts führt in jedem Gate zu einer Ablehnung, nie zu einem Durchlass.
- Ein AWS-Key in einer ungetrackten Datei `Prüfung.py` oder `my secret.py` blockiert.
- Der Review-Fall von (1, 0) auf (0, 9) ergibt `vorlage`.
- Ein Frontmatter-Wert mit Anführungszeichen ist nach zehn Schreibvorgängen unverändert.
- 50 parallele Aufrufe von `log.sh` ergeben 50 gültige JSON-Zeilen.
- Der Kontext-Alarm feuert bei einem Transkript über 200 KB mit 75 % Füllung.
- `python3 tests/gate/run.py --against main` zeigt nur die gewollten Abweichungen, jede im PR begründet.
- Die CI ist grün auf macOS und Linux.

## Entscheidungen, die beim Planen fallen

- **Fehlervertrag als System-ADR?** Der Exit-Vertrag (0, 1, 2) und „Gates schließen, Beobachter laufen weiter“ gelten künftig für den ganzen Kern. Vorschlag: als System-ADR 0019 festhalten, damit M1 und M2 darauf aufbauen.
- **Testwerkzeug:** `unittest` aus der Standardbibliothek oder `pytest` nur in der CI? Vorschlag: `unittest`, damit lokal ohne Installation läuft, was die CI prüft.
- **Version:** Patch-Version des Plugins anheben (0.13.0 auf 0.13.1), weil sich Verhalten in Fehlerfällen ändert.

## Ablauf

- Branch `fix/core-safety-net` von `main`.
- Reihenfolge: zuerst D (Testgerüst und CI), dann A, dann B, dann C. Jeder Befund ein eigener Commit mit Test.
- Ein PR für das ganze Paket, Beschreibung mit Liste der Befunde und den gewollten Abweichungen im Gate-Test.
