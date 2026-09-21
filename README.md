# keel

Schlankes Agentensystem für autonome Softwareentwicklung als Claude-Code-Plugin. Der Mensch entscheidet über das Was, die Rollen lösen das Wie. Zustand lebt in Dateien, Übergaben sind feste Artefakte, Prüftore blockieren statt zu bitten.

Das vollständige Konzept steht in [docs/konzept.md](docs/konzept.md).

## Aufbau

keel ist der **Motor** und für alle Projekte gleich. Alles Projektspezifische liegt im Projekt unter `.keel/`.

```
.claude-plugin/   Manifest und Marketplace
agents/           Rollen: planer, tester, entwickler, reviewer
skills/           Befehle: /keel:init, /keel:vorhaben <name>
hooks/            Übergabeprüfung, Budget, Prüftor, Schutzhooks, Rohdaten
scripts/          frontmatter.py, config.py, gate.sh, init.sh
templates/keel/   Vorlagen für den Ordner .keel/ eines Projekts
templates/settings/  Deny-Regeln für .claude/settings.json
docs/             Konzept und System-ADRs
```

Sprachen: Prompts, Vorlagen und Artefakte deutsch, Code und Skripte englisch.

## Ein Vorhaben durchführen

Der Mensch (oder später der Product Owner) schreibt die Problemstellung mit Akzeptanzkriterien nach `.keel/work/plans/<name>.md` mit `status: problemstellung`. Dann in einer Claude-Code-Session im Projekt:

```
/keel:vorhaben <name>
```

Die Haupt-Session ist der Lead. Er ruft der Reihe nach Tester (Abnahmetests), Planer und je Aufgabe Tester, Entwickler und Reviewer als Subagents auf. Hooks prüfen jede Übergabe an der Grenze über das Frontmatter der Dateien unter `.keel/work/`, zählen das Budget pro Rolle, schützen die Tests des Testers vor dem Entwickler und lassen das Prüftor beim Beenden des Entwicklers laufen. Am Ende steht ein Abnahmenachweis unter `.keel/work/acceptance/`. Bei Testeinspruch oder erschöpftem Budget bleibt das Vorhaben `blockiert`, bis ein Mensch entscheidet.

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

Scheibe 2 von 4: ein vollständiger Aufgabenzyklus läuft. Erster Testlauf am 2026-09-21 im Beispielprojekt: 3 Aufgaben, 3 Reviews in Runde 1 bestanden, 1 berechtigter Testeinspruch, Abnahme grün. Tagesrhythmus (Auditor, Vorlagen, Startcheck) und Lernschleife (Kennzahlen, Coach, Backlog-Adapter) folgen.
