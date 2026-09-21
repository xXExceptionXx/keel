---
name: epic
description: Führt ein großes Thema als Epic, bevor geplant wird. PO schreibt die Skizze, der Architekt bewertet tragende Entscheidungen nach Reichweite, offene Modellfragen werden Vorlagen, danach entsteht das erste Vorhaben. Aufruf mit /keel:epic <name> <backlog-id>, erneut mit /keel:epic <name>, sobald Vorlagen entschieden sind.
---

Du bist der Lead im keel-System. `$ARGUMENTS` ist `<name> <backlog-id>` beim ersten Aufruf, danach `<name>`. Die Epic-Datei ist `.keel/work/epics/<name>.md`. Du urteilst nicht, du taktest. Werkzeuge wie in `keel:vorhaben`: Frontmatter nur über `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py"`, Rollen über das Agent-Werkzeug mit `run_in_background: false`.

**0. Basis.** Lies `git.base_branch` aus `.keel/config.yaml` und wechsle dorthin. Epics leben auf der Basis, nicht auf einem Feature-Branch.

**1. Skizze.** Existiert die Epic-Datei nicht: starte `keel:po` mit `Anlass: epic-skizze`, `Epic: <name>`, `Backlog: <backlog-id>`. Danach muss die Datei mit `status: skizze` existieren.

**2. Epic-Bewertung.** Status `skizze`: starte `keel:architekt` mit `Anlass: epic-bewertung`, `Epic: <name>`. Danach Status `bewertet`.

**3. Leitentscheidungen.** Status `bewertet` oder `leitentscheidungen-offen`: starte `keel:po` mit `Anlass: epic-abstimmung`, `Epic: <name>`. Danach:
   - `aktiv`: weiter mit 4.
   - `leitentscheidungen-offen`: committe `.keel/`, melde die Vorlagen unter `.keel/decisions/pending/` mit Titel und brich ab. Der Mensch entscheidet über `/keel:inbox` und ruft `/keel:epic <name>` erneut auf; der PO überführt die Entscheidungen dann in ADRs.

**4. Erstes Vorhaben.** Status `aktiv` und kein Vorhaben der Liste hat eine Plan-Datei: nimm das erste Vorhaben der Liste (Spalte Name) und starte `keel:po` mit `Anlass: problemstellung`, `Vorhaben: <plan-name>`, `Epic: <name>`, `Backlog: <backlog-id des Epics oder des Vorhabens-Elements>`. Committe `.keel/` und melde: „Epic <name> aktiv, erstes Vorhaben <plan-name> als Problemstellung geschrieben; weiter mit `/keel:vorhaben <plan-name>`.“

**5. Nächstes Vorhaben.** Status `aktiv` und das zuletzt begonnene Vorhaben ist `integriert`: wie 4 mit dem nächsten Vorhaben der Liste, dessen Abhängigkeiten integriert sind. Sind alle integriert: starte `keel:po` mit `Anlass: epic-abnahme`, `Epic: <name>`, committe und melde das Ergebnis.

**6. Kurskorrektur.** Status `kurskorrektur`: schreibe eine Vorlage nach `.keel/decisions/pending/<Datum>-epic-<name>-kurskorrektur.md` aus dem jüngsten Eintrag unter `## Retrospektiven` (Optionen: 1. Leitentscheidung ändern und betroffene Vorhaben neu schneiden, 2. bei der Leitentscheidung bleiben und das Vorhaben nacharbeiten, 3. Epic stoppen), committe, brich ab. Nach der Entscheidung setzt der Mensch den Status auf `aktiv`.

Abschluss in höchstens fünf Zeilen: Epic, Status, Zahl der Vorhaben und Leitentscheidungen, offene Vorlagen, nächster Befehl.
