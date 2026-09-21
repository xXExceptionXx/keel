# keel

Schlankes Agentensystem für autonome Softwareentwicklung als Claude-Code-Plugin. Der Mensch entscheidet über das Was, die Rollen lösen das Wie. Zustand lebt in Dateien, Übergaben sind feste Artefakte, Prüftore blockieren statt zu bitten.

Das vollständige Konzept steht in [docs/konzept.md](docs/konzept.md).

## Aufbau

keel ist der **Motor** und für alle Projekte gleich. Alles Projektspezifische liegt im Projekt unter `.keel/`.

```
.claude-plugin/   Manifest und Marketplace
agents/           Rollen: planer, tester, entwickler, reviewer, auditor
skills/           Befehle, siehe Tagesrhythmus
hooks/            Übergabeprüfung, Budget, Prüftor, Schutzhooks, Rohdaten
scripts/          frontmatter.py, config.py, gate.sh, init.sh
templates/keel/   Vorlagen für den Ordner .keel/ eines Projekts
templates/settings/  Deny-Regeln für .claude/settings.json
docs/             Konzept und System-ADRs
```

Sprachen: Prompts, Vorlagen und Artefakte deutsch, Code und Skripte englisch.

## Tagesrhythmus

| Befehl | Wer | Was |
| --- | --- | --- |
| `/keel:tagesstart` | Lead | Startcheck, bei Rot Reparaturaufgabe; Übergabenotiz des Vortags in Kurzform; Inbox; Vorhaben mit Status; Empfehlung |
| `/keel:vorhaben <name>` | Lead | Ein Vorhaben von der Problemstellung bis zum Abnahmenachweis, siehe unten |
| `/keel:tagesabschluss` | Lead | Übergabenotiz aus Artefakten, gesamte Testsuite, Commit, Tag `day-<Datum>` |
| `/keel:audit` | Auditor | Prüfbericht über den Diff seit dem letzten Tag; `/keel:audit woche` prüft den Gesamtstand |
| `/keel:inbox` | Mensch | Offene Vorlagen, Pläne zur Abnahme, Blockaden, letzter Prüfbericht |
| `/keel:reparatur` | Lead | Reparaturaufgabe bei rotem Startcheck, läuft auch aus tagesstart und vorhaben heraus |

Der Mensch entscheidet Vorlagen unter `.keel/decisions/pending/`, nimmt Pläne mit `status: abgenommen` ab und hebt Blockaden auf. Alles andere läuft ohne ihn.

## Ein Vorhaben durchführen

Der Mensch (oder später der Product Owner) schreibt die Problemstellung mit Akzeptanzkriterien nach `.keel/work/plans/<name>.md` mit `status: problemstellung`. Dann in einer Claude-Code-Session im Projekt:

```
/keel:vorhaben <name>
```

Die Haupt-Session ist der Lead. Er ruft der Reihe nach Tester (Abnahmetests), Planer und je Aufgabe Tester, Entwickler und Reviewer als Subagents auf. Hooks prüfen jede Übergabe an der Grenze über das Frontmatter der Dateien unter `.keel/work/`, zählen das Budget pro Rolle, schützen die Tests des Testers vor dem Entwickler und lassen das Prüftor beim Beenden des Entwicklers laufen. Die Arbeit läuft auf `vorhaben/<name>`; am Ende steht ein Abnahmenachweis unter `.keel/work/acceptance/`. Nimmt der PO ab (`status: abgenommen`), integriert der nächste Aufruf: Merge nach `main`, Abnahmetests in die Regressionssuite, Branch weg. Bei Testeinspruch, erschöpftem Budget oder Befunden nach zwei Review-Runden schneidet der Planer die Aufgabe neu: an Ort und Stelle, ersetzt durch kleinere, oder verworfen. Erst beim zweiten Neuschnitt derselben Aufgabe schreibt der Lead eine Vorlage und das Vorhaben bleibt `blockiert`, bis ein Mensch entscheidet.

Rohdaten für die Lernschleife landen außerhalb des Repos unter `~/.keel-metrics/<projekt>/`.

## Installation in einem Projekt

```bash
claude plugin marketplace add xXExceptionXx/keel
claude plugin install keel@keel --scope project
```

Danach in einer Claude-Code-Session im Projekt:

```
/keel:init
```

Der Marketplace wird in den User-Settings des Rechners eingetragen, nicht im Projekt. In `.claude/settings.json` des Projekts landet nur `enabledPlugins`. Auf jedem neuen Rechner ist der erste Befehl deshalb einmal nötig, danach reicht der zweite.

Das legt `.keel/` mit Vorlagen an, verlinkt `.claude/skills` dorthin, ergänzt Deny-Regeln für destruktive Befehle in `.claude/settings.json` und fügt `@.keel/CLAUDE.md` in die `CLAUDE.md` des Projekts ein. Bestehende Dateien werden nie überschrieben.

## Stand

Scheibe 3 von 4: Tagesrhythmus komplett. Erprobt im Beispielprojekt am 2026-09-21: drei Vorhaben abgenommen und integriert, davon eines vollständig auf einem `vorhaben/`-Branch mit Merge nach Abnahme; Audit mit Befunden, Reparatur nach simuliertem Defekt, Neuschnitt nach Testeinspruch. Offen ist die Lernschleife: Kennzahlen, Coach, Backlog-Adapter.
