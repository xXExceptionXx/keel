# Arbeitspaket 4: Hook-Dispatcher

2026-10-05 · Schritt M2 aus `docs/kern-architektur.md`. Grundlage: offene Befunde in `docs/kern-befunde.md` (U1 bis U4, N1, N2, Leistung), System-ADR 0019 (Fehlervertrag), 0020 (Paket und Ablage), 0021 (Wiedervorlagen). Geplant am 2026-10-05 im Plan-Modus, Umsetzung auf `feature/hook-dispatcher`.

**Stand 2026-10-05: umgesetzt**, System-ADR 0022, Version 0.17.0. Messung: `Edit` einer Rolle 102 ms statt 315 ms, `Bash` des Leads 99 ms statt 178 ms. Abweichungen vom Entwurf stehen unter „Entscheidungen“; dazu: Der Briefing-Stand liegt als eigene Datei neben dem Session-Merker, weil `wiedervorlage.py` ihn umschreibt. Der Guard prüft je Befehlsteil, weil Pythons Regex-Engine bei sehr langen Befehlen quadratisch wurde. `tests/gate/hooks.py` vergleicht die übrigen Gates mit dem vorigen Stand. Ein Probelauf `/keel:vorhaben` bis zur Abnahme steht aus, weil es kein Testprojekt gibt; ein Lauf von Claude Code 2.1.285 im Fixture-Projekt (Bash, abgelehnte und erlaubte Agent-Aufrufe, Stop, SessionEnd) lief ohne `hook_error`.

## Ausgangslage

Arbeitspaket 2 hat das Paket `lib/keel` mit der Schicht `store` gebaut, Arbeitspaket 3 hat `domain/adr.py`, `domain/followup.py`, `services/agenda.py` und `integrations/git.py` ergänzt (PR #2, Version 0.16.0). Die Hooks sind aber weiter elf Bash-Skripte mit rund 1100 Zeilen, die ihre Regeln selbst tragen und je Aufruf viele Prozesse starten:

- `agent-gate.sh` (238 Zeilen) und `agent-stop.sh` (319 Zeilen) enthalten die Ein- und Austrittsregeln aller Rollen als `case`-Blöcke. Jede Prüfung ist ein eigener Aufruf von `frontmatter.py`, jedes Feld des Payloads ein eigener `jq`.
- Gemessen in `kern-befunde.md`, Abschnitt 6: ein `Edit` einer Rolle kostet rund 1,0 s (14 × `jq`, 5 × `python3`), ein `Bash` des Leads rund 0,22 s.
- Offene Befunde, alle in den Hooks: U1 bis U3 (Pfade in den Schutzregeln nicht normalisiert), U4 (Lücken in `guard.sh`), N1 (Werkzeugzähler ohne Sperre), N2 (`pending-<rolle>` nicht atomar, bleibt nach einer abgelehnten Freigabe zehn Minuten liegen).
- Der Fehlervertrag aus System-ADR 0019 ist in `hooks/lib.sh` mit `trap`, `KEEL_DONE` und der Notbremse nachgebaut. Er funktioniert, aber jede neue Prüfung muss ihn von Hand richtig benutzen (`gate_fail` statt `exit`, `|| rc=$?` statt nacktem Aufruf).

Das Plugin läuft in keinem Projekt. Abwärtskompatibilität für Laufzeit-Dateien ist nicht nötig.

## Ziel

Jedes Hook-Ereignis hat in `hooks/hooks.json` genau einen Eintrag, der einen Python-Prozess startet. Der Dispatcher in `interfaces/hooks.py` liest den Payload einmal, ruft die zuständigen Prüfungen mit typisierten Werten und setzt den Fehlervertrag an einer Stelle durch. Die Regeln stehen danach in Python, getestet und ohne `jq`.

Verhalten nach außen bleibt gleich, außer dort, wo ein Befund behoben wird. Sicherung sind die Vertragstests unter `tests/contract/` (unverändert grün) und ein Vergleichstest gegen `main`, der für alle Gates gilt, nicht nur für `agent-gate.sh`.

## Umfang

### A. Dispatcher und Startpunkt

- `bin/keel hook <ereignis>` mit `<ereignis>` aus `pre-tool-use`, `post-tool-use`, `subagent-start`, `subagent-stop`, `stop`, `session-start`, `session-end`, `user-prompt-submit`, `notification`.
- `interfaces/hooks.py`: Payload lesen und gegen ein kleines Schema prüfen, je Ereignis und Matcher die Prüfungen in fester Reihenfolge aufrufen (heute etwa `PreToolUse` auf `Bash`: guard, tool-gate, log), Ergebnis in das Antwortformat von Claude Code übersetzen (`permissionDecision: deny`, `decision: block`, `additionalContext`).
- Jede Prüfung ist als Gate oder Beobachter deklariert. Gate: jede Ausnahme wird Exit 2 mit Meldung. Beobachter: jede Ausnahme wird ein `hook_error`-Ereignis, der Aufruf läuft weiter. Die Notbremse für `subagent-stop` (dritter interner Fehler desselben Agenten) zieht in den Dispatcher.
- Ein kleiner `sh`-Startpunkt vor Python, damit ein fehlendes oder zu altes `python3` nicht als Exit 127 durchlässt: Er liest den Payload, prüft Python 3.9 oder neuer und endet sonst mit Exit 2. Ausnahme wie heute (`keel_gate_init keel-only`): Aufrufe, die keel nicht betreffen, laufen auch ohne Python durch.
- `jq` wird für die Hooks nicht mehr gebraucht. `keel doctor` meldet es nur noch, wenn andere Teile es brauchen.

### B. Die Hooks in Python, in dieser Reihenfolge

Reihenfolge aus `kern-architektur.md`: zuerst das Risikoreichste, dann das Häufigste. Jeder Schritt ist ein eigener Commit, nach jedem sind alle Tests grün, und das Bash-Skript wird im selben Commit zur Weiterleitung oder entfällt.

1. **Agent-Ende** (`agent-stop.sh`): Austrittsregeln je Rolle, Budget, Abschlussnachricht, ADR-Stufe, Prüftor, Diff-Grenze, Compliance-Scan. Das Prüftor (`gate.sh`) läuft als Unterprozess mit eigenem Timeout unter dem Hook-Timeout von 600 s; läuft es ab, blockiert das Gate.
2. **Werkzeugaufruf** (`tool-gate.sh`): Werkzeugbudget, Testschutz, Sperre des Kennzahlen-Ordners, `budget_slow`.
3. **Protokoll und Alarm** (`log.sh`, `context-alarm.sh`): ein Aufruf schreibt die Protokollzeile und prüft den Kontext; das Transkript wird einmal von hinten gelesen.
4. **Agent-Start und -Freigabe** (`agent-start.sh`, `agent-gate.sh`): Eintrittsregeln, Fälligkeiten, Parken des Bezugs. `scripts/flow.py shell` und das `eval` entfallen, die Regeln kommen direkt aus Python.
5. **Skill und Session** (`skill-gate.sh`, `session-gate.sh`, `briefing-stop.sh`).
6. **Guard** (`guard.sh`), siehe Entscheidungen.

### C. Laufzeitzustand mit Sperren (N1, N2)

- `store/runtime.py`: Zustand je Agent (Bezug, Rolle, Start, Zähler, Merker für `slow` und `stopfail`, ADR-Stand) an einer Stelle, mit `file_lock` aus `store/io.py`. Die einzelnen Dateien `agent-<id>.*` dürfen zu einer JSON-Datei je Agent zusammengehen.
- Werkzeugzähler: Lesen, Erhöhen und Schreiben unter einer Sperre je Agent. Ein leerer oder kaputter Zähler blockiert (heute: Durchlass).
- `pending-<rolle>`: atomar anlegen (`O_EXCL`). Ein Eintrag, zu dem nie ein `SubagentStart` kam, wird beim nächsten Gate als verwaist erkannt und ersetzt, statt die Rolle zehn Minuten zu sperren. Woran „verwaist“ sicher zu erkennen ist, klärt der Plan (siehe Entscheidungen).

### D. Schutzregeln mit normalisierten Pfaden (U1 bis U3)

- Testschutz und Budget-Ausnahme vergleichen Pfade nach `os.path.realpath` relativ zum Projekt, nicht als Text. `…/./tests/a.test.js`, `…//tests/…` und `.keel/work/../../src/app.js` werden erkannt.
- Die Sperre des Kennzahlen-Ordners prüft auch `~/.keel-metrics`, `$KEEL_METRICS_DIR` und `${KEEL_METRICS_DIR}`. In der Doku wird sie als Leitplanke beschrieben, nicht als Grenze.
- Schreibzugriffe über Bash auf Testdateien (`echo x > tests/a.test.js`) lassen sich mit Mustern nicht dicht prüfen. Der Plan klärt, ob Deny-Regeln in den Settings (`merge_settings.py`) sie abdecken oder ob es bei einer dokumentierten Lücke bleibt.

### E. Guard (U4)

- Fehlende Muster ergänzen: Force-Push per Refspec (`+main`), `rm -rf "$HOME"`, lange Optionen (`--recursive --force`), `find … -delete`, `cd / && rm -rf …`, `git push --delete` ohne Prüfung auf Merge.
- Je Muster ein Vertragstest mit dem Befehl aus `kern-befunde.md`.
- `docs/system.md` beschreibt den Guard als zweites Netz hinter den Deny-Regeln.

### F. Lebenszeichen, Ebene 1 und 2

- Ebene 1: Der Dispatcher hört zusätzlich auf `SessionEnd` und `Notification` und protokolliert sie. Bei `SessionStart` merkt er sich die Prozess-ID des Claude-Prozesses (vorher prüfen, ob der Elternprozess des Hooks wirklich Claude Code ist).
- Ebene 2: Kontextmanager `activity(name, ref)` in `store/runtime.py` mit Marker (Prozess-ID, Start, Bezug). Prüftor, Compliance-Scan und Fälligkeiten melden sich damit an. Ein Marker mit totem Prozess gilt als verwaist; `keel doctor` meldet ihn.
- `hook_error` trägt Hook, Ereignis und Meldung, damit der Monitor ihn später zuordnen kann.
- Die Anzeige im Monitor und die Statuszeile gehören zu M6, ebenso Ebene 3 (Runner).

### G. Leistung

- Vor dem ersten Umbau eine Messung je Hook mit festem Payload (Median aus 20 Läufen), als Skript unter `tests/perf/`, damit sie wiederholbar ist.
- Ziel: ein `Edit` einer Rolle unter 150 ms über alle Hooks des Ereignisses, ein `Bash` des Leads unter 100 ms. Gemessen wird vor und nach dem Umbau, das Ergebnis steht im System-ADR.

### H. Tests

- Vertragstests unter `tests/contract/` bleiben in Sollwerten und Prüfungen unverändert. Erlaubt sind nur Anpassungen an Pfaden von Laufzeit-Dateien, wenn C sie zusammenlegt; jede davon steht im PR.
- `tests/gate/` wird zum Vergleichstest für alle Gates: Er schickt dieselben Payloads an den Arbeitsstand und an einen Git-Stand (`--against origin/main`) und vergleicht Antwort, Exit-Code, geparkte Bezüge und Ereignisse. Neue Fälle für `agent-stop`, `tool-gate`, `skill-gate` und `guard`.
- Unit-Tests für den Dispatcher: Gate mit Ausnahme ergibt Exit 2, Beobachter mit Ausnahme ergibt `hook_error` und Exit 0, Notbremse beim dritten Fehler.
- Neue Vertragstests für N1 (50 parallele Aufrufe ergeben 50), N2 (abgelehnte Freigabe sperrt nicht), U1 bis U4, zuerst als `expectedFailure` gegen den alten Stand.
- Der Architekturtest gilt für `interfaces/hooks.py` und die neuen Module.

## Nicht im Umfang

- Regeln als Daten in `domain` (Status, Übergänge, Ein- und Austrittsregeln als Tabelle): M3. Dieses Paket überträgt die Regeln nach Python, ordnet sie aber noch nicht um.
- Kommandozeile für Skills und Agenten (`keel next`, `keel done`, Skills rufen nur noch `keel …`): M4 und M5.
- Monitor auf dem gemeinsamen Lesemodell, Statuszeile, Runner-Zustand: M6.
- Entfernen von `scripts/`: M7. Skripte, die nur noch Hooks bedient haben, dürfen schon entfallen, wenn kein Skill und kein Agent sie aufruft.
- Die offenen Fragen P1 bis P3 aus dem Probelauf. P3 (`budget.context_window`) berührt den Kontext-Alarm, wird aber getrennt entschieden.

## Abnahme

- `hooks/hooks.json` hat je Ereignis einen Eintrag auf `bin/keel hook`; in `hooks/` liegt keine Regel mehr in Bash (Ausnahme nach Entscheidung: Guard).
- Alle Vertragstests aus den Paketen 1 bis 3 grün, Vergleichstest gegen `main` ohne unbegründete Abweichung, Architekturtest grün, CI auf Linux und macOS grün.
- Ohne `python3` im PATH blockiert jedes keel-Gate mit Exit 2; Aufrufe ohne keel-Bezug laufen durch.
- Eine Ausnahme in einem Gate ergibt Exit 2 mit Meldung, in einem Beobachter ein `hook_error` und Durchlass.
- 50 parallele Werkzeugaufrufe einer Rolle ergeben den Zählerstand 50. Eine abgelehnte Freigabe sperrt die Rolle nicht.
- Die Umgehungen aus U1 bis U4 werden abgelehnt.
- Ein `Edit` einer Rolle braucht über alle Hooks unter 150 ms (Median), gemessen mit `tests/perf/`.
- `SessionEnd` und `Notification` stehen im Protokoll; ein Prüftor, das läuft, hat einen Marker, und ein verwaister Marker erscheint in `keel doctor`.
- Ein Probelauf `/keel:vorhaben` in einem frischen Testprojekt bis zur Abnahme ohne `hook_error`.

## Entscheidungen, die beim Planen fielen (2026-10-05)

- **Wie weit nach Python:** Der heiße Pfad (guard, tool-gate, log, Kontext-Alarm) läuft ganz im Prozess. Agent-Gate und Agent-Stop nutzen Frontmatter, Konfiguration und ADR im Prozess. `due.py`, `compliance_scan.py`, `review.py`, `pflege.py`, `models.py` und `wiedervorlage.py` bleiben bis M3/M4 Unterprozesse. Die Regeln werden eins zu eins als Funktionen je Rolle unter `services/hooks/` übertragen; Tabellen in `domain` folgen in M3.
- **Guard:** geht nach Python, als eigenes Modul, beschrieben als zweites Netz.
- **Laufzeitzustand:** neues Format, das nur `store/runtime.py` kennt: `state/agents/<id>.json`, `state/pending/<rolle>.json`, `state/sessions/<sid>.json`. `kern-gesperrt` bleibt eine Textdatei, weil der Mensch sie von Hand löscht. `lage.py`, Monitor, `keel doctor` und `wiedervorlage.py` lesen über die API. Vertragstests prüfen dieselben Werte über Helfer in `harness.py`. Keine Migration. Umgestellt wird zuletzt: Bis dahin kapselt `store/runtime.py` das alte Format, damit portierte und noch nicht portierte Hooks dieselben Dateien teilen.
- **Verwaistes `pending`:** `SubagentStart` liefert keine `tool_use_id` (Hook-Doku, Claude Code 2.1.285). Regel deshalb: Ein Eintrag ist verwaist, wenn kein Agent dieser Rolle läuft und er älter als 30 Sekunden ist. Er wird dann ersetzt und als `pending_verwaist` protokolliert.
- **Bash-Schreibzugriffe auf Tests (U1):** dokumentierte Lücke, der Testschutz wird als Leitplanke beschrieben.
- **Lebenszeichen:** Ebene 1 (`SessionEnd`, `Notification`) und Ebene 2 (Marker laufender Operationen) werden protokolliert, die Anzeige folgt in M6. Die Prozess-ID der Session bleibt draußen, weil sie nicht dokumentiert ist.
- **Hooks laufen heute parallel** (Hook-Doku). Der Dispatcher führt alle passenden Schritte nacheinander in einem Prozess aus, auch nach einer Ablehnung, damit Zähler und Protokoll gleich bleiben; die erste Ablehnung gewinnt.
- **System-ADR und Version:** System-ADR 0022, Version 0.17.0.

## Danach

| Paket | Inhalt |
| --- | --- |
| 5 | Messung K0 und B0 aus den Protokollen eines Testprojekts; braucht einige Wochen Betrieb |
| 6 | M3: Regeln als Tabellen in `domain`, oder K1 (Rollenkern und Auftrag je Anlass über `SubagentStart`), je nachdem, was der Betrieb dringender zeigt |
| 7 | A1: Graph und Kennzahlen für Bestandsprojekte |
