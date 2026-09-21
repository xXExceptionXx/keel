---
nummer: 0004
titel: Konfigurierbarer Basis-Branch, main bleibt manuell; Code durchgehend Englisch
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes:
hypothese: Projekte mit develop oder staging brauchen keine Sonderbehandlung; der Lead fasst main nie an
---

# 0004: Konfigurierbarer Basis-Branch, main bleibt manuell; Code durchgehend Englisch

## Kontext

xXExceptionXx entwickelt in seinen Projekten auf `develop` oder `staging`; der Weg nach `main` ist ein bewusster, manueller Schritt. ADR 0003 hatte `main` als Basis fest verdrahtet. Außerdem soll in seinen Projekten alles im Code Englisch sein, nur die keel-Artefakte sind Deutsch.

## Entscheidung

- `.keel/config.yaml` bekommt `git.base_branch` (Standard `main`), `git.feature_prefix` (Standard `feature/`) und `git.fix_prefix` (Standard `fix/`).
- Vorhaben-Branches zweigen von der Basis ab, die Integration mergt in die Basis. `/keel:tagesstart` beginnt auf der Basis. Der Lead berührt `main` nur, wenn `main` die Basis ist.
- Der Guard erlaubt das Löschen von Remote-Branches nur mit den konfigurierten Präfixen.
- Sprachregel: Artefakte unter `.keel/` Deutsch. Bezeichner, Kommentare, Testbeschreibungen, Commit-Nachrichten, Branch-Namen und Dateinamen Englisch. Ein Projekt kann in `.keel/architektur.md` eine andere Konvention festlegen; dann gilt die.

## Folgen

- Das Beispielprojekt wurde vor dieser Regel gebaut und trägt deutsche Bezeichner. Es bleibt so, neue Vorhaben dort folgen der Regel; die Mischung ist ein bekannter Zustand des Testbetts, kein Vorbild.
- Aufgaben-IDs wie `V1-T01` und `R-<Datum>` bleiben, sie sind opake Schlüssel der Artefakte.
