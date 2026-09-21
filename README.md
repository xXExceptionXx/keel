# keel

Schlankes Agentensystem für autonome Softwareentwicklung als Claude-Code-Plugin. Der Mensch entscheidet über das Was, die Rollen lösen das Wie. Zustand lebt in Dateien, Übergaben sind feste Artefakte, Prüftore blockieren statt zu bitten.

Das vollständige Konzept steht in [docs/konzept.md](docs/konzept.md).

## Aufbau

keel ist der **Motor** und für alle Projekte gleich. Alles Projektspezifische liegt im Projekt unter `.keel/`.

```
.claude-plugin/   Manifest und Marketplace
skills/           Befehle wie /keel:init
hooks/            Prüftore und Schutzhooks
scripts/          Skripte, die Skills und Hooks gemeinsam nutzen
templates/keel/   Vorlagen für den Ordner .keel/ eines Projekts
templates/settings/  Deny-Regeln für .claude/settings.json
docs/             Konzept und System-ADRs
```

Sprachen: Prompts, Vorlagen und Artefakte deutsch, Code und Skripte englisch.

## Installation in einem Projekt

```bash
claude plugin marketplace add xXExceptionXx/keel
claude plugin install keel@keel --scope project
```

Danach in einer Claude-Code-Session im Projekt:

```
/keel:init
```

Das legt `.keel/` mit Vorlagen an, verlinkt `.claude/skills` dorthin, ergänzt Deny-Regeln für destruktive Befehle in `.claude/settings.json` und fügt `@.keel/CLAUDE.md` in die `CLAUDE.md` des Projekts ein. Bestehende Dateien werden nie überschrieben.

## Stand

Scheibe 1 von 4: Skelett mit Init, Vorlagen und Schutzhooks. Rollen, Prüftore, Tagesrhythmus und Lernschleife folgen.
