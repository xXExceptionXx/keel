# Befunde am Kern: Reparaturliste

2026-10-01 · Prüfung des Python-Kerns (`scripts/`) und der Hooks (`hooks/`). Zwei Prüfdurchgänge mit Experimenten in einem Scratch-Projekt, die schwersten Befunde zusätzlich im Code nachgeprüft. Geprüft wurde der Stand auf dem Branch `review-threshold` (PR #3). `review.py` und `pflege.py` gibt es nur dort, noch nicht auf `main`.

Diese Liste ist zum Abarbeiten gedacht. Das Sicherheitsnetz (Abschnitt 1) sollte vor dem Umbau des Kerns stehen, der Rest geht im Umbau auf (siehe `kern-architektur.md`).

Legende: **belegt** = im Experiment nachgestellt, **gelesen** = aus dem Code abgeleitet.

## Stand der Behebung

Arbeitspaket 1 (`docs/arbeitspakete/01-sicherheitsnetz.md`, System-ADR 0019, Version 0.14.0), 2026-10-01:

| Befund | Stand |
| --- | --- |
| S1 bis S8 | behoben, je mit Vertragstest unter `tests/contract/` |
| F1, F2, F3 | behoben, mit Vertragstests |
| F4 | geklärt und behoben: Der lexikografische Vergleich war in ADR 0018 bewusst festgelegt. Ergänzt um die Bedingung, dass die Summe aus blockierend und wichtig nicht steigt; das ADR-Beispiel 4/0 → 0/2 bleibt Fortschritt, 1/0 → 0/9 nicht mehr |
| N3, N5 | behoben; dazu neu N7: getippte `/keel:`-Befehle erreichten das Hook-Protokoll nie, obwohl der Monitor sie dort sucht |
| Beim Umsetzen zusätzlich gefunden | `guard.sh` ließ wegen SIGPIPE unter `pipefail` lange Befehle durch; ungebundene Variablen und Abbrüche innerhalb von Funktionen endeten ohne Exit 2; `deny` protokollierte vor der Ausgabe der Entscheidung; `guard.sh` protokollierte seine Ablehnungen nicht. Alles behoben |
| U1 bis U4, N1, N2 | behoben in Arbeitspaket 4, siehe unten |

Arbeitspaket 2 (`docs/arbeitspakete/02-kern-fundament.md`, System-ADR 0020, Version 0.15.0), 2026-10-01:

| Befund | Stand |
| --- | --- |
| F5 | behoben: Der Markdown-Backlog ändert nur die Zeilen des betroffenen Eintrags; Vertragstest `test_backlog.py` |
| F6 | behoben: Das Routing schreibt den Bericht nach jedem gerouteten Befund atomar zurück; Vertragstest `test_routing.py`. Rest-Fenster: ein Abbruch genau zwischen Anlegen und Zurückschreiben |
| F7 | behoben: ein Codec für Frontmatter und Konfiguration (`lib/keel/store/codec.py`), Schema mit Defaults; Vertragstest `test_config_codec.py` |
| F8, F9 | behoben: Ereignisse liest nur noch `lib/keel/store/events.py`, tolerant und in UTC mit Zeitzone; Berichte lesen Frontmatter tolerant; Vertragstest `test_robust_reading.py` |
| N4 | behoben: Laufzeit-Ordner `<name>-<hash>`, berechnet nur in `lib/keel/store/paths.py`; Vertragstest `test_runtime_key.py`. Ohne Migration, weil das Plugin in keinem Projekt läuft |
| N6 | behoben: `atomic_write` und `file_lock` (`lib/keel/store/io.py`) an allen genannten Schreibstellen; Vertragstest `test_concurrency.py` |

### Aus dem Review von PR #13 (2026-10-01)

Zwei Reviews (Fable, Opus 5.5) des Pakets. Alle Befunde sind auf demselben Branch behoben, jeweils mit einem Test, der vor der Korrektur fehlschlug.

| Befund | Stand |
| --- | --- |
| `gate.sh` meldete „grün“, wenn der Codec die Konfiguration ablehnte (leerer Testbefehl) | behoben, Exit 2; `test_config_gates.py` |
| `\b` in `pii_patterns` wurde durch JSON-Escapes zu einem Steuerzeichen, der Scan meldete „frei“ | behoben, nur noch bekannte Escapes, sonst Fehler mit Zeile; Template mit einfachen Anführungszeichen |
| `frontmatter set` mit Zeilenumbruch oder ungültigem Schlüssel schrieb eine unlesbare Datei | behoben, Schlüssel geprüft, Selbstprobe vor dem Schreiben; `test_frontmatter_write.py` |
| `metrics.py` stürzte bei unlesbarer Konfiguration ab; `--since` mit Datum als UTC-Mitternacht | behoben, Exit 2; Datum als lokale Mitternacht wie `due.py` |
| `atomic_write` ersetzte Symlinks durch Dateien | behoben, folgt dem Link |
| Projektschlüssel hing unter macOS von der Groß-/Kleinschreibung ab | behoben, gespeicherte Schreibweise |
| Eine unlesbare ADR sperrt alle Rollen ohne sichtbare Ursache | Sperre bleibt (Entscheidung des Menschen); Meldung mit Datei und Zeile, `keel doctor` prüft alle Artefakte |
| `agent-stop.sh` las Frontmatter per `grep` | behoben, `frontmatter.py find`; Muster-Test |
| `skill-gate.sh` prüfte `keel_paths` in einer `\|\|`-Liste nicht | behoben |
| Monitor startete je Poll `git`, `jq` und las Protokolle ganz | behoben, schnelle Prüfung mit 60 s Zwischenspeicher, Ende der Protokolle |
| `events.read` verwarf bei Schnitt auf Zeilengrenze eine volle Zeile | behoben |
| Backlog: CRLF, IDs unter fremden Überschriften, Fließtext unter Einträgen | behoben, im Vertragstest belegt |
| `flow.py` ließ unlesbare Dateien still weg | behoben, Feld `unlesbar`, im Monitor sichtbar |
| `bin/keel` ließ sich von einem Ordner `keel/` im Projekt verdecken | behoben, Start über `lib/keel_main.py` |
| Werte mit führendem `*`, `!`, `&` wurden abgelehnt | als Text gelesen (Entscheidung des Menschen) |
| Sperren je Metrics-Wurzel | bewusst so, in System-ADR 0020 beschrieben; `keel doctor` prüft Schreibrechte |

Arbeitspaket 4 (`docs/arbeitspakete/04-hook-dispatcher.md`, System-ADR 0022, Version 0.17.0), 2026-10-05:

| Befund | Stand |
| --- | --- |
| U1, U3 | behoben: Testschutz und Budget-Ausnahme vergleichen Pfade nach `realpath`; Vertragstest `test_tool_gate.py`. Schreibzugriffe über Bash auf Testdateien bleiben eine dokumentierte Lücke |
| U2 | behoben als Leitplanke: auch `~/.keel-metrics`, `$KEEL_METRICS_DIR`, `$HOME/…`; Vertragstest `test_tool_gate.py` |
| U4 | behoben: Refspec-Force-Push, `rm` mit langen Optionen oder `"$HOME"`, `find -delete`, `cd /` mit `rm -rf`, Löschen nur gemergter Remote-Branches; Vertragstest `test_guard.py`. Der Guard bleibt das zweite Netz |
| N1 | behoben: Zähler unter Sperre in `lib/keel/store/runtime.py`; 50 parallele Aufrufe ergeben 50 (`test_tool_gate.py`) |
| N2 | behoben: Startmarke exklusiv angelegt, verwaist nach 30 s ohne laufenden Agenten der Rolle (`test_pending.py`) |
| Beim Umsetzen zusätzlich gefunden | Pythons Regex-Engine wurde bei Befehlen mit Tausenden Teilen quadratisch (40 s je Aufruf im Test); der Guard prüft jetzt je Befehlsteil. `budget.<rolle>_<schlüssel>` aus dem Schema greift weiter nur, wenn die Datei ihn setzt (wie in Bash, im Template stehen alle) |

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

**Stand 2026-10-05:** Mit dem Dispatcher (System-ADR 0022) braucht ein `Edit` einer Rolle über alle Hooks 102 ms statt 315 ms Wartezeit (622 ms Rechenzeit), ein `Bash` des Leads 99 ms statt 178 ms; gemessen mit `tests/perf/hooks.py`. Der Stand vorher:

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

## Offen aus dem Probelauf 2026-10-01

Probelauf im Beispielprojekt mit 0.14.0, Lead auf Opus 5.5, Briefing auf Fable. Die Teile, die Projekt-ADR 0022 und 0023 betreffen, sind in `docs/arbeitspakete/03-wiedervorlagen.md` übernommen. Diese drei Motor-Themen stehen nur hier; das Beispielprojekt wird gelöscht.

| Nr. | Befund | Quelle | Stand |
| --- | --- | --- | --- |
| P1 | **Korridor „Einwände des Supervisors“ verlangt Einwände ohne Anlass.** Ein Einwand entsteht laut `agents/supervisor.md` nur, wenn der Mensch gegen die Empfehlung des Supervisors entscheidet. Ist das nie passiert, ist 0 richtig, der Korridor `1-10` meldet trotzdem eine Verletzung und erzeugt Druck zu erfundenem Widerspruch. Optionen des Coaches: (1) Kennzahl je Abweichung von der Empfehlung, Feld `empfehlung` im Frontmatter der Vorlage, ohne Abweichung „n/a“, Korridor 50–100 %; (2) Untergrenze 0, das Warnsignal entfällt; (3) nichts ändern. Empfehlung des Coaches: Option 1. | Coach-Vorlage `2026-10-01-coach-einwand-korridor.md` | vom Menschen bewusst offen gelassen, ist noch zu entscheiden |
| P2 | **Zähllücke beim Modellwechsel des Supervisors.** Briefings laufen als Hauptsitzung, nicht als Rollenlauf, und zählen deshalb nicht für die zehn Läufe aus System-ADR 0015. Nach zehn Tagen standen 2 von 10; ein Vergleich wäre frühestens nach Wochen möglich. Zu klären: Briefing-Sitzungen als Läufe des Supervisors zählen (Ereignis aus dem Skill oder aus `session-gate`), oder für den Supervisor eine eigene, niedrigere Schwelle. | Coach-Bericht 2026-10-01, Abschnitt System-ADR 0015 | offen |
| P3 | **`budget.context_window` steht auf 200 000, Opus 5.5 und Fable 5.1 haben 1M.** Der Kontext-Alarm kommt damit bei 10 % des echten Fensters. Der Coach hält 100 000 Tokens als absolute Grenze für Kontextpflege weiter für vernünftig und schlägt eine Anhebung erst vor, wenn der Alarm messbar zu früh kommt. Zu entscheiden: den Schlüssel bewusst als absolute Grenze umbenennen und beschreiben (etwa `budget.context_tokens: 100000`) statt als Fenstergröße mit Prozent. | Coach-Bericht 2026-10-01, Abschnitt Modellzuordnung | offen |

Weitere Beobachtungen aus dem Lauf, ohne eigenen Befund:
- Die Fälligkeit des Coaches nach einem Modellwechsel greift mitten im Vorhaben und unterbricht die Arbeit (im Lauf 76 Werkzeugaufrufe). Kandidat für eine spätere Justierung: die Fälligkeit erst nach der laufenden Aufgabe greifen lassen.
- Der Coach weist auf `/doctor prompt-audit` (Claude Code 2.1.283) hin, das Agents und Skills auf Prompt-Muster für ältere Modelle prüft; ein sinnvoller Begleitschritt zum Wechsel auf Opus 5.5, ohne gemessenes Problem.
- Zwei Leitlinien hat der Supervisor vorgeschlagen, sie sind nicht bestätigt: „Eine wartende Frage braucht einen Träger, den ein Skript sieht; ein Vermerk im Protokoll ist keiner.“ und „Eine Schutzmaßnahme, die nie ausgelöst hat, wird erst auf Melden zurückgestuft und erst nach belegtem Auslösen entfernt.“ Beide sind als Grundsätze für den Motor brauchbar, unabhängig vom Projekt.

## Vorschlag zur Reihenfolge

**Vor dem Merge von PR #3:** F4 (Review-Schwelle) und F2 (leere Werte in `review.py`).

**Sicherheitsnetz, als eigenes Reparatur-Vorhaben vor dem Umbau:**
1. S1 bis S8: alle Gates schließen bei Fehlern, Compliance-Scan prüft Git und Dateinamen, Timeout für das Prüftor.
2. F1 und F3: Frontmatter-Escaping und Kontext-Alarm.
3. N5: Protokoll atomar, damit die Messung aus den Konzepten auf sauberen Daten beruht.
4. Je Korrektur ein Test mit festem Sollwert, dazu eine einfache CI.

**Im Umbau des Kerns:** alle übrigen Punkte. Die meisten verschwinden strukturell, weil es dann eine Stelle für Pfade, Ereignisse, Frontmatter, Konfiguration, atomares Schreiben und Exit-Codes gibt.
