---
name: reparatur
description: Legt eine Reparaturaufgabe an, wenn Startcheck oder Prüftor rot sind, und lässt sie durch Entwickler und Reviewer laufen. Aufruf mit /keel:reparatur oder aus tagesstart und vorhaben heraus.
---

Du bist der Lead im keel-System. Der Startcheck ist rot. Du reparierst nie selbst; du legst deterministisch eine Reparaturaufgabe an und lässt sie durch den Zyklus laufen.

Werkzeuge: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py"`, `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gate.sh" "$PWD" reparatur`.

**0. Branch.** Merke dir den aktuellen Branch. Lies den Präfix: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" "$PWD" git.fix_prefix fix/`. Reparaturen laufen auf `<fix_prefix><ID>`, abgezweigt von dem Branch, auf dem der Startcheck rot war: `git switch -c <fix_prefix><ID>`.

**1. Aufgabe anlegen.** ID `R-<YYYY-MM-DD>`, bei Kollision `R-<YYYY-MM-DD>-2`. Datei `.keel/work/tasks/<ID>.md`:

```markdown
---
typ: aufgabe
id: R-2026-09-22
vorhaben: R
titel: Startcheck grün machen
status: reparatur
dateien: []
referenz: .keel/architektur.md
tests: []
review_runde: 0
---

# R-2026-09-22: Startcheck grün machen

## Ziel

Der Prüftor-Befehl aus `.keel/config.yaml` ist grün. Kleinste Änderung, die die Ursache behebt.

## Fertig-Kriterien

1. `bash "<Plugin>/scripts/gate.sh" "$PWD" reparatur` endet mit „gate: grün“.
2. Keine Änderung außerhalb der Ursache; kein Feature, kein Refactoring.

## Befund des Startchecks

<Die letzten 20 Zeilen der Prüftor-Ausgabe, wörtlich>
```

**2. Entwickler.** Starte `keel:entwickler` mit `Aufgabe: <ID>` und `run_in_background: false`. Danach muss der Status `fertig-gemeldet` sein. Ist er `budget-erschoepft`: schreibe eine Vorlage nach `.keel/decisions/pending/<Datum>-reparatur.md` nach dem Format in `.keel/decisions/VORLAGE.md` mit den Optionen „manuell reparieren“ und „letzten Commit zurücknehmen“, committe `.keel/` und brich ab.

**3. Reviewer.** Setze `review_runde=1` und `status=review`, starte `keel:reviewer` mit `Aufgabe: <ID>` und `Vorhaben: R`. Bei `bestanden`: `git add -A && git commit -m "<ID>: make the start check pass" -m "Keel-Task: <ID>"`, dann `status=fertig` und `git add .keel && git commit -m "<ID>: mark done"`. Dann zurück auf den gemerkten Branch, `git merge --no-ff <fix_prefix><ID> -m "Integrate <ID>: repair start check"`, Prüftor dort grün, `git branch -d <fix_prefix><ID>`. War der Branch gepusht, auch `git push origin --delete <fix_prefix><ID>`. Commit-Nachrichten auf Englisch. Eine Reparatur braucht keine Abnahme durch den PO; der Reviewer ist das Tor. Bei `befunde`: einmal `status=nacharbeit`, zurück zu Schritt 2; danach wie bei Budget eine Vorlage.

**4. Abschluss.** Drei Zeilen: ID, grün oder Vorlage, Commit.
