# Befunde am Kern: Reparaturliste

2026-10-01 · Prüfung des Python-Kerns (`scripts/`) und der Hooks (`hooks/`). Zwei Prüfdurchgänge mit Experimenten in einem Scratch-Projekt, die schwersten Befunde zusätzlich im Code nachgeprüft. Geprüft wurde der Stand auf dem Branch `review-threshold` (PR #3). `review.py` und `pflege.py` gibt es nur dort, noch nicht auf `main`.

Diese Liste ist zum Abarbeiten gedacht. Das Sicherheitsnetz (Abschnitt 1) sollte vor dem Umbau des Kerns stehen, der Rest geht im Umbau auf (siehe `kern-architektur.md`).

Legende: **belegt** = im Experiment nachgestellt, **gelesen** = aus dem Code abgeleitet.

## 1. Sicherheitsnetz: Gates, die bei Fehlern durchlassen

Claude Code blockiert nur bei Exit-Code 2 oder einer ausdrücklichen Ablehnung (`permissionDecision: deny`, `decision: block`). Jeder andere Fehler ist ein „nicht blockierender Fehler“, und der Aufruf geht durch.

| Nr. | Befund | Fundstelle | Stand | Behebung |
| --- | --- | --- | --- | --- |
| S1 | Ohne `jq` im PATH endet `tool-gate.sh` mit Exit 0, `agent-gate.sh` mit 127. Rollen starten ungeprüft, Budgets greifen nicht. Ursache: `field` scheitert in `keel_role "$(field …)"`, die Rolle bleibt leer. | `hooks/lib.sh:7`, `hooks/tool-gate.sh:6` | belegt | `command -v jq python3 >/dev/null \|\| exit 2` am Anfang jedes Gates. |
| S2 | Kaputter Payload: `agent-gate.sh` endet mit Exit 5 (Parse-Fehler von `jq` unter `set -e`), der Agent startet. | `hooks/agent-gate.sh` | belegt | `trap '…; exit 2' ERR` in jedem Gate. |
| S3 | `agent-stop.sh` bricht unter `set -e` mit Exit 1 ab und lässt den Stopp ungeprüft zu, ohne `agent_stop`-Ereignis. Auslöser: Neuschnitt ohne passenden Plan (`grep -l … \| head` mit pipefail), Plan des Architekten ohne `status` (`st="$($FM get …)"`), gleiches Muster an weiteren Stellen. | `hooks/agent-stop.sh:42,45,130,158,246` | belegt | `trap … exit 2`, fehlende Felder ausdrücklich behandeln. |
| S4 | Compliance-Scan: Ein Absturz (Exit-Code außer 0, 3, 4, 5) fällt durch alle Fälle des `case`, die Aufgabe geht durch. | `hooks/agent-stop.sh:235` | gelesen | Auffangfall `*) block_stop …`. |
| S5 | Compliance-Scan ignoriert die Exit-Codes von Git. Ungültiges `--base` oder ein Repo ohne HEAD ergibt einen leeren Diff und damit „frei“. | `scripts/compliance_scan.py:66` | belegt | Git-Fehler als Exit 2 melden. |
| S6 | Compliance-Scan prüft ungetrackte Dateien mit Umlaut oder Leerzeichen im Namen nicht. `ls-files` quotet die Namen, `.split()` zerlegt sie, `except OSError: continue` überspringt still. Ein AWS-Key in `Prüfung.py` oder `my secret.py` ergibt „frei“. | `scripts/compliance_scan.py:83,89` | belegt | `git ls-files -z`, am Nullbyte trennen. |
| S7 | Fälligkeiten: Eine Ereigniszeile ohne `ts` bringt `due.py` zum Absturz (`KeyError`). `agent-gate.sh` überspringt das Tor dann (`\|\| true`), `session-gate.sh` schließt es, `briefing_needed.py` meldet „Briefing nötig“. Dieselbe Störung wirkt je nach Ort gegenteilig. | `scripts/due.py:92`, `hooks/agent-gate.sh:36`, `scripts/briefing_needed.py:17` | belegt | Einheitlicher Exit-Vertrag: 0 nein, 1 ja, 2 interner Fehler. Bei 2 schließen alle Gates. |
| S8 | Das Prüftor läuft im Stop-Hook ohne Timeout. Dauert die Suite länger als das Standard-Timeout des Hooks, wird der Hook abgebrochen, und das gilt als nicht blockierend. | `hooks/agent-stop.sh:225`, `hooks/hooks.json` | gelesen | `timeout` in `hooks.json` setzen, `gate.sh` mit eigenem Timeout, bei Abbruch blockieren. |

## 2. Fehler mit falschem Ergebnis oder Datenverlust

| Nr. | Befund | Fundstelle | Stand | Behebung |
| --- | --- | --- | --- | --- |
| F1 | `frontmatter.py set` beschädigt Werte mit Anführungszeichen bei jedem Schreiben derselben Datei, auch wenn ein anderes Feld gesetzt wird. Beim Schreiben maskiert `json.dumps`, beim Lesen werden nur die äußeren Anführungszeichen entfernt. Aus `Er sagt "Hallo": ok` wird nach drei Schreibvorgängen `Er sagt \\\"Hallo\\\": ok`. | `scripts/frontmatter.py` (`_quote`, `_scalar`) | belegt | Beim Lesen JSON-Strings mit `json.loads` entmaskieren. Test für den Round-Trip. |
| F2 | Ein leerer Wert (`notiz:`) wird als leere Liste gelesen, nicht als leerer Text. Folgefehler: `review.py` stürzt bei `anmerkung:` mit `TypeError` ab. | `scripts/frontmatter.py`, `scripts/review.py:130` | belegt | Leerer Wert ist leerer Text, Liste nur mit folgenden `- `-Zeilen. |
| F3 | Kontext-Alarm feuert praktisch nie. `tail -c 200000` schneidet mitten in eine Zeile, `jq -s` scheitert, `\|\| echo 0` setzt den Verbrauch auf 0. Im Beispielprojekt sind die Transkripte 560 bis 720 KB groß, und es gibt kein einziges `context_alarm`-Ereignis. | `hooks/context-alarm.sh:14` | belegt | Zeilenweise mit `jq -R 'fromjson?'` lesen wie in `transcript_model`, oder in Python rückwärts lesen. |
| F4 | Review-Schwelle vergleicht Tupel lexikografisch. Von (1 blockierend, 0 wichtig) auf (0, 9) gilt als „Befunde sinken“ und ergibt `nacharbeit` statt `vorlage`. **Steckt in PR #3, vor dem Merge beheben.** | `scripts/review.py:182` | gelesen | Regel ausdrücklich: Keine Kategorie steigt, und mindestens eine sinkt. Test dazu. |
| F5 | Backlog (Markdown-Adapter) löscht bei einer Statusänderung Felder außerhalb von `FIELDS` (`Prio:`, `Akzeptanz:`), mehrzeilige Werte, Fließtext und Abschnittsüberschriften. | `scripts/backlog.py:41-78` | belegt | Unbekannte Zeilen roh mitführen oder nur die betroffene Zeile ändern. |
| F6 | `route_findings.py` ist nicht idempotent. Bricht ein späteres Anlegen ab, sind frühere Einträge schon angelegt, aber nicht vermerkt. Der nächste Lauf legt sie doppelt an. | `scripts/route_findings.py:46,123` | gelesen | Bericht nach jedem gerouteten Befund atomar zurückschreiben. |
| F7 | Konfiguration: `#` wird auch innerhalb von Anführungszeichen als Kommentar abgeschnitten. `repo: "o/r#1"` wird zu `o/r`. Nur zwei Ebenen, keine Listen. Ein eigener Parser für die dritte Ebene in `backlog.py` hat dieselbe Schwäche. | `scripts/config.py`, `scripts/backlog.py:217-231` | belegt | Ein Parser für das ganze Schema, siehe Kernarchitektur. |
| F8 | Robustheit bei kaputten Werten: `metrics.py` stürzt bei einer Ereigniszeile ohne `ts`, bei `runde: zwei` und bei fehlerhaftem `datum` ab. `lage.fm` fängt `UnicodeDecodeError` nicht, eine einzige Nicht-UTF-8-Datei ergibt im Monitor Fehler 500. `backlog show` ohne ID ergibt `IndexError`. | `scripts/metrics.py:106,111,136,175,182`, `scripts/lage.py:30` | belegt | Tolerantes Lesen an einer Stelle, Fehler pro Datei melden statt abstürzen. |
| F9 | Zeitstempel: teils mit Zeitzone gelesen (`lage.py`), teils ohne (`models.py`, `metrics.py`, `due.py`). `due.py` vergleicht UTC-Ereignisse mit dem lokalen `date.today()`. Ein `--since` mit Offset ergibt `TypeError`. | `scripts/lage.py:163`, `scripts/models.py:57`, `scripts/metrics.py:106`, `scripts/due.py:92` | gelesen | Überall UTC mit Zeitzone, eine Funktion zum Lesen. |

## 3. Schutzregeln, die sich umgehen lassen

| Nr. | Befund | Fundstelle | Stand | Behebung |
| --- | --- | --- | --- | --- |
| U1 | Testschutz erlaubt `…/proj/./tests/a.test.js`, `…/proj//tests/…` und jeden Schreibzugriff über Bash (`echo x > tests/a.test.js`). | `hooks/tool-gate.sh:22-29` | belegt | Pfade mit `realpath` normalisieren, Bash-Schreibzugriffe über Deny-Regeln in den Settings. |
| U2 | Sperre des Kennzahlen-Ordners sucht nur den expandierten Pfad als Text. `cat $KEEL_METRICS_DIR/…` und `~/.keel-metrics/…` kommen durch. | `hooks/tool-gate.sh:15` | belegt | Auch unexpandierte Formen prüfen. Ehrlich als Leitplanke ausweisen, nicht als Grenze. |
| U3 | Budget-Ausnahme für `.keel/work/` erlaubt `…/.keel/work/../../src/app.js` über dem Limit. | `hooks/tool-gate.sh:42,63` | belegt | Normalisieren, dann Präfix prüfen. |
| U4 | `guard.sh` lässt durch: `git push origin +main` (Force-Push per Refspec), `rm -rf "$HOME"`, `rm --recursive --force /etc`, `find / -delete`, `cd / && rm -rf usr`, `git push origin --delete feature/x` ohne Prüfung auf Merge. | `hooks/guard.sh` | belegt | Muster ergänzen, in der Doku als zweites Netz ausweisen. Eine Denylist bleibt löchrig. |

## 4. Gleichzeitige Zugriffe und Ablage

| Nr. | Befund | Fundstelle | Stand | Behebung |
| --- | --- | --- | --- | --- |
| N1 | Werkzeugzähler ist Lesen-Ändern-Schreiben ohne Sperre. 20 parallele Aufrufe ergaben 16. Eine leere `.calls`-Datei ergibt Exit 1, also Durchlass. | `hooks/tool-gate.sh:55-57` | belegt | `flock` je Agent. |
| N2 | `pending-<rolle>`: Prüfen und Anlegen nicht atomar. Lehnt der Mensch den Agent-Aufruf nach dem Gate ab, bleibt die Datei liegen, und die Rolle ist 10 Minuten als „läuft noch“ gesperrt. | `hooks/agent-gate.sh:28,211` | gelesen | Atomar anlegen, beim nächsten Gate verwaiste Einträge erkennen. |
| N3 | Feste Pfade `/tmp/keel-gate-err` und `/tmp/keel-stop-err` an 73 Stellen. Parallele Sessions überschreiben sich die Fehlermeldungen. | `hooks/*.sh` | gelesen | `mktemp`. |
| N4 | Ablage nach Ordnername: `KEEL_METRICS_DIR/<basename>`. Zwei Projekte namens `app` teilen Ereignisse, `pending`-Sperren und Fälligkeiten. Fünf Stellen in Python, drei in `lib.sh`. | `scripts/lage.py:283`, `scripts/models.py:25`, `scripts/metrics.py:91`, `scripts/due.py:83`, `scripts/check_references.py:30`, `hooks/lib.sh:16,23,69` | gelesen | Schlüssel aus Ordnername plus Hash des absoluten Pfads, an einer Stelle berechnet. |
| N5 | `log.sh` schreibt lange Zeilen in mehreren `write()`-Aufrufen. Zwei Zeilen im Protokoll des Beispielprojekts sind ineinander geschrieben (eigene Aufgabe angelegt). Außerdem landen ganze Payloads samt `tool_response` im Log, also möglicherweise Secrets. | `hooks/log.sh:11` | belegt | Ein einzelnes `write` auf `O_APPEND` plus `flock`. Payload auf die nötigen Felder kürzen. |
| N6 | Schreiben ohne Atomarität und ohne Sperre in `review.update`, `pflege.save`, `backlog._save`, `route_findings`, `merge_settings`, `monitor.pid`. `pflege sammeln` vergibt IDs per `max+1`. | `scripts/review.py:72`, `scripts/pflege.py:58`, `scripts/backlog.py:78` | gelesen | `atomic_write` (Temp-Datei, `fsync`, `os.replace`), `flock` für Pflegeliste und Backlog. |

## 5. Kleinere Punkte

- `keel-run.sh:32`: `grep -qiE "…|resets"` greift auch bei normaler Ausgabe mit „resets“, dann folgen 30 Minuten Wartezeit. `keel-run.sh:15`: `$1` ungequotet im AppleScript-String.
- `metrics.py:129`: toter Code (`if True`).
- Monitor: Ausnahmetexte im Fehler 500, `files()` ruft `stat()` ohne Fehlerbehandlung. Sonst ist der Monitor sauber abgesichert: nur `127.0.0.1`, Host-Prüfung gegen DNS-Rebinding, `safe_under` mit `resolve()`, nur `.md`.
- Das Supervisor-Modell `claude-fable-5-1` steht hart an drei Stellen: `hooks/skill-gate.sh:41`, `hooks/session-gate.sh:13`, `scripts/keel.sh:13`.

## 6. Leistung

Gemessen, sequenziell:

| Aufruf | Prozesse | Zeit |
| --- | --- | --- |
| `Edit` einer Rolle (tool-gate, log zweimal, context-alarm) | 14 × `jq`, 5 × `python3` | rund 1,0 s |
| `Bash` des Leads | 10 × `jq`, 2 × `python3` | rund 0,22 s |

Jedes `field` ist ein eigener `jq`-Prozess, `role_limit` startet `config.py` bis zu zweimal. Ein Python-Start kostet rund 35 ms. Ein Dispatcher mit einem Prozess je Hook käme auf rund 40 bis 60 ms. Dazu wachsen `due.py` und der Monitor mit der Historie, weil sie bei jedem Aufruf `events.jsonl` vollständig lesen.

## 7. Testlage

- `tests/gate/` testet nur `agent-gate.sh`, und nur im Vergleich mit einer älteren Version. Fehler, die in beiden stecken, fallen nicht auf.
- Ungetestet: `agent-stop.sh` (größter Regelblock), `tool-gate.sh`, `guard.sh`, `context-alarm.sh`, `skill-gate.sh`, `session-gate.sh`, `log.sh`, der Review-Schiedsspruch, `pflege.py`, der Round-Trip von Frontmatter und Backlog, `models.switches`, die Kennzahlen, `compliance_scan.py`. Fehlerpfade, fehlende Werkzeuge und Parallelität sind gar nicht abgedeckt.
- Es gibt keine CI.
- Mit wenig Aufwand testbar, weil schon reine Funktionen: `flow.satisfied`, `models.switches`, `review.findings`, `pflege.rows`.

## Vorschlag zur Reihenfolge

**Vor dem Merge von PR #3:** F4 (Review-Schwelle) und F2 (leere Werte in `review.py`).

**Sicherheitsnetz, als eigenes Reparatur-Vorhaben vor dem Umbau:**
1. S1 bis S8: alle Gates schließen bei Fehlern, Compliance-Scan prüft Git und Dateinamen, Timeout für das Prüftor.
2. F1 und F3: Frontmatter-Escaping und Kontext-Alarm.
3. N5: Protokoll atomar, damit die Messung aus den Konzepten auf sauberen Daten beruht.
4. Je Korrektur ein Test mit festem Sollwert, dazu eine einfache CI.

**Im Umbau des Kerns:** alle übrigen Punkte. Die meisten verschwinden strukturell, weil es dann eine Stelle für Pfade, Ereignisse, Frontmatter, Konfiguration, atomares Schreiben und Exit-Codes gibt.
