# Arbeitspaket 2: Fundament des Kerns

2026-10-01 · Schritt M1 aus `docs/kern-architektur.md`. Grundlage: `docs/kern-befunde.md` (offene Befunde), System-ADR 0019 (Fehlervertrag). Zum Planen im Plan-Modus, dann Umsetzung auf einem eigenen Branch.

## Ausgangslage

Arbeitspaket 1 hat das Sicherheitsnetz gespannt (PR #8, Version 0.14.0): Gates schließen bei Fehlern, 66 Vertragstests unter `tests/contract/` prüfen Hooks und Skripte von außen, eine CI läuft auf Linux und macOS. Der Kern ist aber weiter ein Bündel von Skripten: Pfade, Ereignisse, Frontmatter und Konfiguration werden an fünf bis zehn Stellen je eigen gelesen und geschrieben, mit je eigenen Fehlern. Die offenen Befunde aus `kern-befunde.md` liegen fast alle genau dort.

## Ziel

Ein Python-Paket `keel` mit der Schicht `store` als einzige Stelle für Pfade, Lesen und Schreiben. Die bestehenden Skripte nutzen sie, statt eigene Kopien zu pflegen. Damit verschwinden die offenen Befunde zur Ablage strukturell, und M2 (Hook-Dispatcher) baut auf einem festen Fundament auf.

Verhalten nach außen bleibt gleich, außer dort, wo ein Befund behoben wird. Die Vertragstests aus Arbeitspaket 1 sind die Sicherung: Sie müssen ohne Änderung grün bleiben.

## Vor dem Start

**Validierungslauf mit 0.14.0.** Ein voller `/keel:vorhaben`-Lauf im Beispielprojekt mit dem aktuellen Plugin-Stand, bis zur Abnahme. Ziel: keine unerwarteten Blockaden durch den Fehlervertrag, `hooks.jsonl` enthält getippte Befehle, keine `hook_error`-Ereignisse ohne Ursache. Was dabei auffällt, wird vor Arbeitspaket 2 behoben. Der Lauf liefert außerdem die ersten sauberen Daten für die spätere Messung (K0, B0).

## Umfang

### A. Paketgerüst

- `lib/keel/` mit den Unterpaketen aus `kern-architektur.md`: zunächst nur `domain/errors.py` und `store/`, dazu `interfaces/cli.py` mit wenigen Befehlen.
- `bin/keel`: Startskript, prüft Python 3.9 oder neuer, ruft die Kommandozeile. Erste Befehle: `keel --version`, `keel doctor`, `keel path <art>` (für die Hooks, siehe B).
- Die Skripte unter `scripts/` importieren das Paket über einen kleinen gemeinsamen Einstieg statt elf `sys.path`-Tricks.
- Ein Architekturtest liest die Importe mit `ast` und prüft die Richtung der Schichten (`domain` importiert nichts aus `store`, `store` nichts aus `services` und so weiter).

### B. Pfade und Projektschlüssel (N4)

- `store/paths.py` berechnet alle Pfade an einer Stelle: Projekt, `.keel/`, Laufzeit-Ordner, Zustand, Protokolle.
- Der Laufzeit-Ordner bekommt einen Projektschlüssel aus Ordnername und kurzem Hash des absoluten Pfads. Zwei Projekte namens `app` teilen sich dann nichts mehr.
- Migration: Gibt es den alten Ordner `~/.keel-metrics/<name>/` und noch keinen neuen, wird er beim ersten Zugriff übernommen. Die Daten aus dem Beispielprojekt bleiben erhalten.
- Die Hooks holen den Pfad über `keel path` statt ihn selbst zu bauen; die heute zehn Stellen in Python und Bash verschwinden.

### C. Ein Codec für Frontmatter und Konfiguration (F7)

- `store/codec.py`: ein strikter YAML-Teilparser für Frontmatter und `.keel/config.yaml`. Verschachtelte Abbildungen, Listen inline und als Block, Text mit und ohne Anführungszeichen samt Escapes, Kommentare nur außerhalb von Anführungszeichen. Was er nicht versteht, lehnt er mit Zeilennummer ab.
- Die Regeln aus Arbeitspaket 1 bleiben: leerer Wert und reiner Kommentar sind leer, gequotete Werte überstehen beliebig viele Schreibvorgänge.
- `frontmatter.py` und `config.py` werden dünne Hüllen um den Codec; ihre Kommandozeile bleibt gleich. Der Handparser in `backlog.py` entfällt.
- Konfiguration mit Schema: Defaults stehen an einer Stelle in `store/config.py`. Ein Test prüft, dass `templates/keel/config.yaml` dazu passt.

### D. Atomares Schreiben und Sperren (N6)

- `store/io.py`: `atomic_write` (Temp-Datei, `fsync`, `os.replace`) und `file_lock` (`fcntl.flock`). `scripts/jsonl.py` geht darin auf.
- Alle Schreibstellen nutzen sie: `frontmatter.py set`, `review.update`, `pflege.save` (mit Sperre, die IDs werden heute per `max+1` vergeben), `backlog._save`, `route_findings`, `merge_settings`, `monitor.pid`.

### E. Ereignisse an einer Stelle (F8, F9)

- `store/events.py`: anhängen (atomar) und lesen (tolerant, UTC mit Zeitzone). Ersetzt die fünf heutigen Varianten in `lage.py`, `models.py`, `metrics.py`, `due.py`, `monitor.py`.
- Kaputte Zeilen, fehlende `ts` und Dateien, die kein UTF-8 sind, werden übersprungen und gezählt, nie zum Absturz.
- Inkrementelles Lesen ist noch nicht nötig, die Schnittstelle soll es aber zulassen (M6).

### F. Datenverlust in Backlog und Routing (F5, F6)

- Der Markdown-Adapter in `backlog.py` ändert nur noch die betroffene Zeile und führt unbekannte Felder, Fließtext und Überschriften unverändert mit.
- `route_findings.py` schreibt den Bericht nach jedem gerouteten Befund atomar zurück, damit ein Abbruch keine Doppelungen erzeugt.

### G. `keel doctor`

- Prüft: Python-Version, `git`, `jq`, Gültigkeit der Konfiguration gegen das Schema, Notbremse (`kern-gesperrt`), verwaiste `pending`-Dateien, kaputte Zeilen in den Protokollen, alter Laufzeit-Ordner ohne Projektschlüssel.
- Ausgabe kurz, mit `--json`. `/keel:hilfe` und `lage.py` nutzen dasselbe.

### H. Tests

- Je Modul in `store` eigene Tests (Round-Trip des Codecs mit den Fällen aus Arbeitspaket 1 und F7, Parallelität von `io` und `events`, Migration der Pfade).
- Die Vertragstests aus Arbeitspaket 1 bleiben unverändert grün. Neue Vertragstests für F5 bis F9, N4 und N6, wieder zuerst als `expectedFailure`.

## Nicht im Umfang

- Hook-Dispatcher, Sperren für Zähler und `pending` (N1, N2), umgehbare Schutzregeln (U1 bis U4), Leistung der Hooks: M2.
- Fachlogik nach `domain` (Status, Übergänge, Regeln): M3.
- Kommandozeile für Skills und Agenten (`keel next`, `keel done`, Git-Befehle): M4 und M5.
- Lebenszeichen im Monitor: Ebene 1 könnte vorgezogen werden, gehört aber sinnvoll zu M2.

## Abnahme

- Alle Vertragstests aus Arbeitspaket 1 grün, ohne dass sie geändert wurden.
- Keine Stelle in `scripts/` oder `hooks/` baut den Laufzeit-Pfad oder liest `events.jsonl` oder Frontmatter noch selbst; ein Test sucht nach den alten Mustern.
- Zwei Projekte mit gleichem Ordnernamen haben getrennte Laufzeit-Ordner; die bestehenden Daten des Beispielprojekts sind nach der Migration lesbar.
- `repo: "o/r#1"` und eine Konfiguration mit Listen und drei Ebenen werden richtig gelesen; Unverständliches wird mit Zeilennummer abgelehnt.
- Eine Statusänderung im Markdown-Backlog lässt alle anderen Zeilen byte-gleich.
- 50 parallele `pflege sammeln` erzeugen keine doppelten IDs.
- Eine `events.jsonl` mit kaputten Zeilen, fehlenden `ts` und Zeitstempeln mit Offset bringt kein Skript zum Absturz.
- `keel doctor` meldet jeden der geprüften Zustände in einem Testprojekt.
- Der Architekturtest ist grün, die CI auf Linux und macOS ebenso.
- Gate-Vergleich gegen `main` ohne unbegründete Abweichung.

## Entscheidungen, die beim Planen fallen

- **Eigener Codec oder vendorter Parser?** Vorschlag: eigener, strikter Teilparser, weil der Umfang klein ist und die Regeln aus Arbeitspaket 1 schon festliegen.
- **Ablage des Pakets:** `lib/keel/` neben `scripts/`, oder `scripts/` wird selbst zum Paket? Vorschlag: `lib/keel/`, `scripts/` bleibt bis M7 als Übergang.
- **Migration des Laufzeit-Ordners:** umbenennen oder kopieren? Vorschlag: umbenennen und einen Hinweis-Symlink unter dem alten Namen lassen, damit ältere Plugin-Stände nicht ins Leere schreiben.
- **System-ADR:** Das Paketgerüst mit Schichten und Projektschlüssel ist eine Strukturentscheidung. Vorschlag: System-ADR 0020, Version 0.15.0.

## Danach

Die sinnvolle Reihenfolge der nächsten Pakete:

| Paket | Inhalt | Warum dann |
| --- | --- | --- |
| 3 | M2: Hook-Dispatcher in Python, ein Prozess je Ereignis, Sperren für Zähler und `pending` (N1, N2), normalisierte Pfade in den Schutzregeln (U1 bis U4), Lebenszeichen Ebene 1 und 2 | baut auf `store` auf; größter Gewinn an Robustheit und Geschwindigkeit |
| 4 | Messung K0 und B0: Ausgangsbasis aus den sauberen Protokollen seit 0.14.0 | braucht ein paar Wochen Betrieb nach dem Validierungslauf, kann parallel zu Paket 3 Daten sammeln |
| 5 | K1: Rollenkern und Auftrag je Anlass für Architekt und PO | braucht den Dispatcher für das Einspielen über `SubagentStart` |
| 6 | A1: Graph und Kennzahlen für Bestandsprojekte | unabhängig, kann jederzeit nach Paket 2 beginnen |
