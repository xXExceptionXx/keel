---
nummer: 0020
titel: Kern als Paket mit Schichten, eine Ablage-Schicht, Laufzeit-Ordner je Projektschlüssel
status: Accepted
datum: 2026-10-01
entscheider: Ich
supersedes:
hypothese: Kein Skript und kein Hook baut mehr selbst einen Pfad, liest Ereignisse oder Frontmatter oder schreibt eine gemeinsame Datei ohne Sperre; ein Test sucht die alten Muster und bleibt grün; die Befunde F5 bis F9, N4 und N6 tauchen in vier Wochen Betrieb nicht wieder auf; M2 (Hook-Dispatcher) baut auf store auf, ohne eine weitere Kopie anzulegen
---

# 0020: Kern als Paket mit Schichten, eine Ablage-Schicht, Laufzeit-Ordner je Projektschlüssel

## Kontext

Der Kern war ein Bündel von Skripten (`docs/kern-architektur.md`). Pfade, Ereignisse, Frontmatter, Konfiguration und Schreibzugriffe wurden an fünf bis zwölf Stellen je eigen behandelt: zwölf `sys.path`-Tricks, fünf Leser für `events.jsonl` mit drei Arten, Zeitstempel zu lesen, sieben eigene `fm()`-Varianten, zwei Parser für die Konfiguration, neun Stellen, die den Laufzeit-Ordner bauten. Nur `jsonl.py` schrieb unter einer Sperre. In diesen Kopien lagen die offenen Befunde aus `docs/kern-befunde.md`:

- F5: Der Markdown-Backlog verlor bei einer Statusänderung unbekannte Felder, Fließtext und Überschriften.
- F6: Das Routing von Prüfbefunden legte nach einem Abbruch Einträge doppelt an.
- F7: Die Konfiguration schnitt `#` auch in Anführungszeichen ab, kannte nur zwei Ebenen und keine Listen.
- F8, F9: Kaputte Ereigniszeilen, fehlende Zeitstempel und Dateien, die kein UTF-8 sind, brachten Skripte zum Absturz; Zeitstempel wurden teils mit, teils ohne Zeitzone verglichen.
- N4: Der Laufzeit-Ordner hieß wie der Projektordner; zwei Projekte namens `app` teilten Ereignisse, Startmarken und Fälligkeiten.
- N6: Pflegeliste, Backlog, Review-Ergebnis, Einstellungen und Monitor-PID wurden ohne Sperre und nicht atomar geschrieben; `pflege sammeln` vergab IDs per `max+1`.

Das Plugin läuft derzeit in keinem Projekt. Abwärtskompatibilität mit Laufzeit-Ordnern oder Dateiformaten von 0.14.0 ist deshalb nicht nötig.

## Entscheidung

**Ein Paket `keel` unter `lib/keel/` mit festen Schichten.** `domain` (Regeln ohne Ein- und Ausgabe, vorerst nur `errors.py`), `store` (Pfade, Codec, Frontmatter, Konfiguration, Schreiben, Ereignisse), `integrations` (später), `services` (vorerst `doctor`), `interfaces` (Kommandozeile). Jede Schicht importiert nur aus den Schichten davor. Nur Standardbibliothek, Python 3.9 oder neuer; das Paket lehnt ältere Versionen mit Exit 2 ab. Ein Architekturtest liest die Importe mit `ast` und prüft Richtung und Herkunft.

**Ein Einstieg.** `bin/keel` startet die Kommandozeile (`keel --version`, `keel doctor`, `keel path`). Die Skripte unter `scripts/` importieren das Paket über `scripts/_keel.py`; die zwölf `sys.path`-Tricks entfallen. `scripts/` bleibt bis M7 als Übergang, `frontmatter.py`, `config.py` und `jsonl.py` sind nur noch Hüllen mit gleicher Kommandozeile.

**Laufzeit-Ordner je Projektschlüssel.** `store/paths.py` berechnet jeden Pfad. Der Laufzeit-Ordner heißt `<ordnername>-<8 Zeichen sha256 des aufgelösten absoluten Pfads>` unter `KEEL_METRICS_DIR` (Standard `~/.keel-metrics`). Hooks holen die Pfade einmal je Aufruf mit `keel path --shell`; `jsonl.py` bekommt das Projekt, nicht die Datei. Es gibt keine Migration alter Ordner; `~/.keel-metrics/<name>/` aus 0.14.0 wird ignoriert und kann gelöscht werden.

**Ein Codec.** `store/codec.py` ist ein strikter YAML-Teilparser für Frontmatter und `.keel/config.yaml`: verschachtelte Abbildungen, Listen als Block und inline, Text roh, in doppelten Anführungszeichen mit JSON-Escapes oder in einfachen; Kommentare nur außerhalb von Anführungszeichen. Werte bleiben Text. Was er nicht versteht (Tabulatoren, `|` und `>`, `{}`, Anker, Tags, Strukturen in Listen, falsche Einrückung), lehnt er mit Datei und Zeile ab. Ein doppelt geschriebener Abschnitt wird zusammengeführt, ein doppelter Schlüssel nimmt den späteren Wert, wie bisher. Die Regeln aus Arbeitspaket 1 bleiben: leer und reiner Kommentar sind leer, gequotete Werte überstehen beliebig viele Schreibvorgänge.

**Konfiguration mit Schema.** Alle Defaults stehen in `store/config.py`; ein Test hält Schema und `templates/keel/config.yaml` gleich. `keel doctor` prüft die Konfiguration gegen das Schema.

**Gemeinsame Dateien unter Sperre und atomar.** `store/io.py`: `atomic_write` (Temp-Datei im selben Ordner, `fsync`, `os.replace`), `file_lock` (`flock` auf eine Sperrdatei unter `<KEEL_METRICS_DIR>/locks/`, damit nichts im Repository landet und das Ersetzen der Datei die Sperre nicht umgeht), `append_line` (ein `write` unter Sperre). Pflegeliste, Backlog, `frontmatter.py set`, Review-Ergebnis, Prüfbericht beim Routing, `merge_settings` und Monitor-PID nutzen sie.

**Ereignisse an einer Stelle.** `store/events.py` hängt an und liest. Lesen ist tolerant: Zeilen, die kein UTF-8, kein JSON-Objekt oder ohne brauchbares `ts` sind, werden übersprungen und gezählt. Jeder Zeitstempel wird zu UTC mit Zeitzone. Lesen ab einem Byte-Offset ist vorgesehen (M6).

**Backlog und Routing ändern nur, was sie meinen.** Der Markdown-Backlog verschiebt bei einer Statusänderung nur die Zeilen des Eintrags; alles andere bleibt byte-gleich. Das Routing schreibt den Bericht nach jedem gerouteten Befund zurück.

**`keel doctor`.** Prüft Python, `git`, `jq`, Konfiguration, Notbremse, verwaiste Startmarken und unlesbare Protokollzeilen. Ausgabe kurz oder mit `--json`; Exit 0 gesund, 1 Befunde, 2 nicht prüfbar. `lage.py` und damit `/keel:hilfe` und der Monitor zeigen dieselben Befunde.

**Belegt durch Tests.** Neue Vertragstests für F5 bis F9, N4, N6 und `keel doctor` wurden zuerst gegen 0.14.0 geschrieben und schlugen dort fehl. Unit-Tests unter `tests/unit/` prüfen jedes Modul von `store`, die Schichtrichtung und dass in `scripts/` und `hooks/` keine alten Muster mehr stehen.

## Folgen

- Die Vertragstests aus Arbeitspaket 1 fragen den Laufzeit-Ordner über `bin/keel path` ab statt ihn selbst zu bauen; sonst sind sie unverändert.
- Eine Frontmatter-Zeile, die der Codec nicht versteht, ließ der alte Parser still weg. Jetzt endet `frontmatter.py` mit Exit 2 und nennt die Zeile; Gates lehnen dann mit dieser Meldung ab. Das betrifft etwa `|`-Blöcke, Tabulatoren, Schlüssel mit Umlauten oder Leerzeichen und eingerückte Zeilen ohne Schlüssel davor.
- Eine Konfiguration, die der Codec nicht versteht, lässt `config.py` mit Exit 2 enden; Gates schließen, Beobachter melden `hook_error`.
- Jeder Hook, der Zustand braucht, startet einmal `bin/keel path` und damit einen Python-Prozess mehr (rund 50 ms), und `config.py` lädt das Paket mit (rund 8 ms je Aufruf). Gemessen am 2026-10-01 auf macOS, Median aus 15 Läufen: `tool-gate.sh` für eine Rolle 176 → 255 ms, `log.sh` 50 → 61 ms, `guard.sh` unverändert 36 ms. M2 holt das mit dem Dispatcher zurück, ein Prozess je Ereignis.
- `hook_error` braucht jetzt `python3`, um den Laufzeit-Ordner zu kennen. Fehlt `python3`, geht dieses Ereignis verloren; die Gates sperren in dem Fall ohnehin (System-ADR 0019).
- Sperrdateien sammeln sich unter `<KEEL_METRICS_DIR>/locks/`, eine je gesperrter Datei, wenige Bytes groß.
- Ein Abbruch genau zwischen dem Anlegen eines Backlog-Eintrags und dem Zurückschreiben des Berichts kann beim Routing weiter eine Doppelung erzeugen; das Fenster ist ein einzelner Schreibvorgang statt des ganzen Laufs.
- Ein Projekt, das auf 0.14.0 lief, beginnt mit einem leeren Laufzeit-Ordner: Kennzahlen, Fälligkeiten und Modellwechsel zählen neu.
