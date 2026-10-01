---
nummer: 0016
titel: Komplexitätsstufen statt Modellnamen, Zuordnung zum Modell in der Konfiguration
status: Proposed
datum: 2026-09-26
entscheider: Ich
supersedes:
hypothese: Mit Stufen und Eskalation sinken die Ausgabe-Tokens pro Aufgabe gegenüber „alles auf dem Session-Modell“, ohne dass Reviews mit Befunden oder Review-Runden steigen; ein neues Modell wird durch eine Zeile in der Zuordnung eingeführt statt durch Änderungen an Agent-Dateien
---

# 0016: Komplexitätsstufen statt Modellnamen

## Kontext

Heute laufen alle Rollen außer dem Supervisor auf dem Modell der Session. Eine leichte Aufgabe kostet damit so viel wie eine schwere, und ein neues Modell erreicht alle Rollen gleichzeitig oder keine. Der Supervisor ist ein Sonderfall mit seinem Modell an zwei Stellen. ADR 0015 macht sichtbar, welches Modell was geleistet hat; dieses ADR schlägt vor, die Wahl zu steuern. Vorgeschlagen, nicht umgesetzt: Die Zuordnung soll auf Zahlen aus ADR 0015 aufbauen, nicht auf Annahmen.

## Vorschlag

1. **Rollen sprechen von Stufen, nicht von Modellen.** Drei Stufen: `einfach`, `mittel`, `schwer`. Welches Modell hinter einer Stufe steht, entscheidet der Mensch in `.keel/config.yaml`:

   ```yaml
   stufen:
     einfach: sonnet
     mittel: opus
     schwer: fable
   rollen:                # feste Stufe für Rollen ohne Aufgabe
     supervisor: schwer
     architekt: schwer
     po: mittel
     auditor: mittel
     coach: mittel
   ```

2. **Der Planer legt die Stufe je Aufgabe fest.** Er kennt Aufgabe und Code. Frontmatter `stufe: mittel`, nach prüfbaren Kriterien, etwa: berührt eine bestehende Schnittstelle, mehr als N Dateien, Nebenläufigkeit oder Migration, kein Referenzbeispiel. Ohne Kriterien ist die Stufe Bauchgefühl und nicht kalibrierbar. Tester, Entwickler und Reviewer der Aufgabe laufen auf ihrer Stufe.
3. **Der Lead wendet an, ein Hook prüft.** Der Lead gibt beim Start der Rolle das Modell der Stufe mit (`model` des Agent-Werkzeugs, es überschreibt das Frontmatter des Agents). `agent-gate.sh` schlägt Stufe und Zuordnung nach und lehnt ab, wenn das Modell nicht passt. Deterministisch, ohne Urteil des Lead.
4. **Eskalation vor Schätzung.** Neuschnitt, erschöpftes Budget oder eine Review-Vorlage (Befunde sinken nicht, System-ADR 0018) heben die Stufe der Aufgabe um eins; der Supervisor bekommt bei der Review-Vorlage „Stufe erhöhen und weitere Runde“ als Option. Die Schätzung ist der Start, die Belege entscheiden. So kostet das teure Modell nur dort, wo das günstigere nachweislich nicht gereicht hat.
5. **Supervisor ohne Sonderfall.** Er bekommt die Stufe `schwer` über `rollen`. `supervisor.model` und das `model` in `agents/supervisor.md` entfallen; das Modell-Gate für das Briefing liest `stufen.schwer`, oder die Stufe des Supervisors, falls überschrieben.
6. **Der Coach kalibriert.** Zwei Kennzahlen kommen dazu: die Verteilung der Stufen (fast alles `schwer` heißt, der Planer stuft zu vorsichtig) und Stufe gegen Ergebnis (`einfach` mit mehr als zwei Review-Runden oder mit Befunden aus der Nacharbeit heißt unterschätzt, `schwer` ohne Befunde vermutlich überschätzt; seit System-ADR 0018 sind Review-Runden nicht mehr auf zwei begrenzt). Vorlagen gehen an die Kriterien der Stufen oder an die Zuordnung. Bei einem neuen Modell ist die Vorlage eine Zeile: „Stufe mittel: opus → …“.

## Offene Punkte vor der Annahme

- Das Agent-Werkzeug nimmt beim `model` bisher nur Aliase (`sonnet`, `opus`, `fable`, `haiku`), keine festen Modell-IDs. Ein Alias folgt still dem neuesten Modell seiner Familie. Die Zuordnung wäre damit zwangsläufig in Aliasen, und das Mitschreiben aus ADR 0015 bleibt der einzige Beleg, welches Modell tatsächlich lief. Vor der Umsetzung prüfen, ob die verwendete Claude-Code-Version feste IDs erlaubt.
- Braucht es eine Stufe für den Lead selbst, oder bleibt er auf dem Session-Modell?
- Erst umsetzen, wenn der Coach nach ADR 0015 mindestens einen Modellvergleich mit Zahlen vorgelegt hat.
