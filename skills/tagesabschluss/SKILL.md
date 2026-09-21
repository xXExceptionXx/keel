---
name: tagesabschluss
description: Schließt den Arbeitstag ab. Schreibt die Übergabenotiz aus den Artefakten, lässt die gesamte Testsuite laufen, committet und setzt das Tages-Tag. Aufruf mit /keel:tagesabschluss, auch aus einer frischen Session.
---

Du bist der Lead im keel-System und schließt den Tag ab. Alles, was du brauchst, steht in Dateien und im Git-Log; nichts kommt aus deinem Gedächtnis. Diese Anweisung funktioniert deshalb auch in einer frischen Session.

Werkzeuge: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py"` für Frontmatter, `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gate.sh" "$PWD" tagesabschluss` für das Prüftor.

## Ablauf

**1. Aufgabengrenze.** `git status --porcelain` darf außer Dateien unter `.keel/` nichts zeigen. Zeigt es Code-Änderungen, ist eine Aufgabe halbfertig: brich ab und melde, welche Dateien betroffen sind. Der Tag endet nur an einer Aufgabengrenze.

**2. Prüftor.** Prüftor laufen lassen. Zusätzlich den Abnahmebefehl aus `.keel/config.yaml` unter `test.acceptance`, falls Pläne mit Status `abnahme-bereit` oder `abgenommen` existieren. Merke dir nur: grün oder rot, mit einer Zeile Zusammenfassung.

**3. Sammeln, nur aus Artefakten.**

```bash
seit="$(git tag -l 'day-*' --sort=-creatordate | head -1)"
git log --oneline "${seit:-$(git rev-list --max-parents=0 HEAD)}..HEAD"
```

Dazu das Frontmatter aller Pläne unter `.keel/work/plans/` und aller Aufgaben unter `.keel/work/tasks/` (nur `dump`, keine Bodies), die Zahl der Dateien unter `.keel/decisions/pending/`, und ADRs mit heutigem Datum unter `.keel/adr/`.

**4. Übergabenotiz schreiben** nach `.keel/work/handoff/<YYYY-MM-DD>.md`:

```markdown
---
typ: uebergabenotiz
datum: 2026-09-22
seit: day-2026-09-21
tests: gruen        # gruen | rot
tag: day-2026-09-22
---

# Übergabenotiz 2026-09-22

**Erledigt:** <Aufgaben-IDs mit Titel, je eine Zeile, aus Commits und Status fertig>

**Offen:** <Pläne mit Status und nächste anstehende Aufgabe; Aufgaben in neuschnitt, blockiert, reparatur>

**Entscheidungen:** <ADRs von heute; Zahl der offenen Vorlagen in decisions/pending/>

**Probleme:** <Testeinsprüche, Budgetverstöße, rote Prüftore aus den Aufgaben-Status; sonst „keine“>

**Werkzeugprobleme:** <aus Abschnitten ## Stand der Aufgaben-Dateien, falls dort Werkzeuge erwähnt sind; sonst „keine“>
```

Jede Zeile ist ein Fakt mit Quelle im Repo. Keine Einschätzungen, keine Erzählung.

**5. Tag setzen.** `git add .keel && git commit -m "Tagesabschluss <Datum>"`, dann `git tag day-<Datum>`. Existiert das Tag schon, nimm `day-<Datum>-2` und trage das ins Frontmatter ein.

**6. Abschluss.** Melde in drei Zeilen: Tag, Tests grün oder rot, Zahl erledigter Aufgaben und offener Vorlagen.
