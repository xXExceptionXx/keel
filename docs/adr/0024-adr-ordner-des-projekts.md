---
nummer: 0024
titel: ADR-Ordner des Projekts neben .keel/adr
status: Accepted
datum: 2026-10-05
entscheider: Ich
supersedes:
hypothese: In einem Projekt mit eigenem ADR-Ordner vergibt keel keine Nummer doppelt, keine Rolle ändert ein ADR dieses Ordners, und der Index in .keel/CLAUDE.md nennt nach der Bestandsaufnahme alle ADRs beider Ablagen
---

# 0024: ADR-Ordner des Projekts neben .keel/adr

## Kontext

Die Bestandsaufnahme im neuen Beispielprojekt hat gezeigt: Projekte, die schon vor keel ADRs geführt haben, legen sie woanders ab (`docs/adr/` mit eigenem Format), keel kennt nur `.keel/adr/`. Der Architekt hat die Lücke selbst als Vorlage gemeldet und seine Nummern von Hand ab 0003 vergeben, damit sie nicht mit `docs/adr/0001` und `0002` kollidieren. Der Index in `.keel/CLAUDE.md` blieb leer, und nichts hielt eine Rolle davon ab, ein ADR in `docs/adr/` zu ändern, an der Stufenprüfung aus System-ADR 0021 vorbei. Das echte Vorbildprojekt hat 28 ADRs in `docs/adr/`.

## Entscheidung

- Neuer Schlüssel `adr.weitere_ordner` (Liste, Standard leer) nennt die ADR-Ordner des Projekts außerhalb von `.keel/adr/`. `init.sh` trägt vorhandene Ordner mit nummerierten Dateien (`docs/adr`, `docs/adrs`, `docs/decisions`, `doc/adr`, `adr`, `decisions`) selbst ein. Ein Ordner außerhalb des Projekts wird abgelehnt.
- `adr.py neu` und `adr.py number` nummerieren nach der höchsten Nummer über alle Ordner weiter.
- Die ADRs dieser Ordner gehören dem Menschen und folgen dem Format des Projekts. Der ADR-Stand beim Rollenstart enthält ihre Prüfsummen; jede Änderung, jede neue und jede gelöschte Datei dort lehnt das Ende der Rolle ab, für jede Rolle einschließlich Supervisor.
- Der Architekt nimmt sie in der Bestandsaufnahme mit Pfad in den Index in `.keel/CLAUDE.md` auf; Reviewer, Supervisor und Hilfe lesen beide Ablagen.
- `keel doctor` meldet genannte Ordner, die es nicht gibt.

## Verworfen

- **Die ADRs nach `.keel/adr/` umziehen.** Das Projekt verlöre seine eigene Ablage und ihr Format, und Verweise im Code und in der Doku würden brechen.
- **Den keel-Ordner auf `docs/adr/` legen.** Die Formate unterscheiden sich (Frontmatter mit `entscheider` gegen Kopf-Tabelle), und die Stufenprüfung braucht das Frontmatter.

## Folgen

- Ein Projekt hat zwei Ablagen mit einer gemeinsamen Nummernfolge.
- Agenda, Kennzahlen und Integrationsprüfung betrachten weiter nur `.keel/adr/`; die ADRs des Projekts sind entschieden und laufen nicht durch Briefing oder Integration.
