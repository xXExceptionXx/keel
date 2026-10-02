# keel

Schlankes Agentensystem für autonome Softwareentwicklung als Claude-Code-Plugin. Der Mensch entscheidet über das Was, die Rollen lösen das Wie. Zustand lebt in Dateien, Übergaben sind feste Artefakte, Prüftore blockieren statt zu bitten.

Das vollständige Konzept steht in [docs/konzept.md](docs/konzept.md), sieben Diagramme zu Rollen, Fälligkeiten, Zuständen, Epics, Hooks, Supervisor- und Lernschleife in [docs/system.md](docs/system.md).

Konzeptentwürfe für die nächsten Schritte, noch ohne ADR:

| Dokument | Worum es geht |
| --- | --- |
| [docs/kern-architektur.md](docs/kern-architektur.md) | Der Kern als Programm: Schichten, ein Einstiegspunkt `keel`, Hook-Dispatcher, Fehlervertrag, Lebenszeichen, Umbau in Schritten M0 bis M7 |
| [docs/kern-befunde.md](docs/kern-befunde.md) | Reparaturliste aus der Prüfung von `scripts/` und `hooks/` |
| [docs/kontext-scope.md](docs/kontext-scope.md) | Kontext per Regel statt per Prosa: Rollenkern und Auftrag je Anlass, Modulgraph, Zielarchitektur mit Ratsche |
| [docs/ablauf-beschleunigen.md](docs/ablauf-beschleunigen.md) | Der Kern erledigt das Feststehende: `keel next` und `keel done`, Werkzeugbefehle, Fakten vorab |
| [docs/arbeitspakete/](docs/arbeitspakete/) | Geschnürte Arbeitspakete zum Planen und Umsetzen |

## Aufbau

keel ist der **Motor** und für alle Projekte gleich. Alles Projektspezifische liegt im Projekt unter `.keel/`.

```
.claude-plugin/   Manifest und Marketplace
agents/           Rollen: supervisor, po, architekt, planer, tester, entwickler, reviewer, compliance, auditor, coach
skills/           Befehle, siehe Tagesrhythmus
hooks/            Übergabeprüfung, Budget, Prüftor, Schutzhooks, Rohdaten
bin/keel          Kommandozeile des Kerns: keel doctor, keel path, keel --version
lib/keel/         Kern als Python-Paket (System-ADR 0020): domain, store (einzige Stelle für Pfade, Frontmatter,
                  Konfiguration, Ereignisse, atomares Schreiben), services (doctor), interfaces (Kommandozeile)
scripts/          Übergang bis zum Umbau-Schritt M7: dünne Skripte auf lib/keel, z. B. frontmatter.py, config.py,
                  gate.sh, due.py, flow.py, lage.py, monitor.py, metrics.py, backlog.py
templates/keel/   Vorlagen für den Ordner .keel/ eines Projekts
templates/settings/  Allow- und Deny-Regeln für .claude/settings.json
docs/             Konzept, System-ADRs, Konzeptentwürfe und Arbeitspakete
tests/contract/   Vertragstests für Hooks und Skripte: python3 -m unittest discover -s tests/contract
tests/unit/       Unit-Tests für lib/keel, Schichtrichtung, alte Muster: python3 -m unittest discover -s tests/unit -t .
tests/run.py      Unit- und Vertragstests parallel, je Testmethode ein Job: python3 tests/run.py [-j N]
tests/gate/       Regressionstest für das Gate: python3 tests/gate/run.py --against main
.githooks/        pre-commit und pre-push: Leak-Prüfung (tests/leak_check.py), auf macOS zusätzlich die Tests mit System-Python und Bash 3.2
```

Sprachen: Prompts, Vorlagen und Artefakte unter `.keel/` deutsch. Alles im Code englisch: Bezeichner, Kommentare, Testbeschreibungen, Commit-Nachrichten, Branch-Namen.

## Im Alltag zwei Befehle, einer für Fragen und einer zum Zusehen

| Befehl | Was passiert |
| --- | --- |
| `/keel:start` | Liest, was fällig ist, und tut es in Reihenfolge: vergessener Tagesabschluss, Audit, Coach, Architektur-Runde, dann das Briefing mit dem Supervisor, falls eines aussteht. Sonst Tagesstart und das nächste Vorhaben. |
| `/keel:stop` | Tagesabschluss mit Übergabenotiz und Tag, Audit, ein Satz zu morgen. |
| `/keel:hilfe [Frage]` | Erklärt den Stand aus Zustand und Ereignissen und nennt den nächsten Befehl. Beobachtet nur: entscheidet nichts, startet keine Rolle, ändert nichts. Auf Wunsch räumt sie Reste auf, legt einen Hinweis für den Coach ab oder meldet einen Motor-Befund als Issue. |
| `/keel:monitor [Port\|stop]` | Öffnet den Ablauf-Monitor auf `http://127.0.0.1:8765/`: ein Ablaufdiagramm mit den Rollen als aktiv, bereit oder gesperrt, welche Rolle gerade woran arbeitet und wer sie gerufen hat, Fälligkeiten, Vorlagen, Ereignisse mit Gründen für Blockaden, je Vorhaben eine Zeitleiste mit Phase, Aufgaben, Reviews und Rollenläufen, dazu alle Übergaben unter `.keel/` als lesbare Dokumente. Beobachtet nur und läuft nach der Session weiter. Das Ablaufdiagramm lädt Mermaid vom CDN jsDelivr, sonst bleibt der Monitor lokal. Mit `monitor.autostart: true` in `.keel/config.yaml` starten ihn die Befehle, die das System arbeiten lassen, von selbst mit. Aus dem Terminal: `python3 <plugin>/scripts/monitor.py <projekt>`. |

Was fällig ist, ergibt sich aus dem Zustand des Projekts, und ein Hook sperrt die Rollen, bis es erledigt ist. Steht ein Briefing an, muss die Session auf dem Modell des Supervisors laufen; ein Hook prüft das und sagt, wie umgestellt wird. Aus dem Terminal wählt `scripts/keel.sh <projekt>` das Modell selbst und öffnet die Session mit `/keel:start`. Coach und Architektur-Runde werden nur fällig, wenn genug Betrieb stattgefunden hat; die Schwellen stehen in `.keel/config.yaml`. Läuft eine Rolle auf einem neuen Modell, meldet der Sessionstart das, und der Coach wird nach zehn Läufen auf dem neuen Modell vorgezogen, um alt und neu zu vergleichen (System-ADR 0015). Die folgenden Befehle sind die Bausteine dahinter und bleiben für den gezielten Einsatz.

## Tagesrhythmus

| Befehl | Wer | Was |
| --- | --- | --- |
| `/keel:briefing` | Supervisor, mit dir | Morgen-Briefing in eigener Session: Supervisor-Entscheidungen des Vortags bestätigen oder kippen, richtungsweisende Vorlagen entscheiden, Leitlinien festhalten. Solange es aussteht, sperrt ein Gate alle Rollen |
| `/keel:tagesstart` | Lead | Startcheck, bei Rot Reparaturaufgabe; Übergabenotiz des Vortags in Kurzform; Inbox; Vorhaben mit Status; Empfehlung |
| `/keel:vorhaben <name> [<backlog-id>]` | Lead | Ein Vorhaben: PO schreibt die Problemstellung aus dem Backlog-Element, Architekt bewertet, Abstimmung, dann Aufgabenzyklus bis zur Abnahme durch den PO und Integration |
| `/keel:epic <name> <backlog-id>` | Lead | Ein großes Thema: PO-Skizze, Epic-Bewertung des Architekten nach Reichweite, Leitentscheidungen als ADR oder Vorlage, dann das erste Vorhaben |
| `/keel:architektur bestand\|woche` | Architekt | Bestandsaufnahme eines bestehenden Projekts oder wöchentliche Drift-Runde |
| Compliance | Hook und Rolle | Scan beim Beenden jedes Entwicklers: Secrets blockieren, neue Abhängigkeiten werden Vorlage, personenbezogene Daten ruft die Compliance-Rolle mit DSGVO-Ermessen |
| `/keel:tagesabschluss` | Lead | Übergabenotiz aus Artefakten, gesamte Testsuite, Commit, Tag `day-<Datum>` |
| `/keel:audit` | Auditor | Prüfbericht über den Diff seit dem letzten Tag; `/keel:audit woche` prüft den Gesamtstand |
| `/keel:inbox` | Mensch | Offene Vorlagen, Pläne zur Abnahme, Blockaden, letzter Prüfbericht |
| `/keel:reparatur` | Lead | Reparaturaufgabe bei rotem Startcheck, läuft auch aus tagesstart und vorhaben heraus |
| `/keel:kennzahlen` | Mensch | Kennzahlen der Lernschleife mit Korridoren, aus Artefakten und Rohdaten |
| `/keel:coach` | Coach | Lernschleife: Hypothesen prüfen, Hinweise des Menschen gegen die Daten prüfen, Umfeld, Justierungen als Vorlagen; monatlich oder bei Korridorverletzung |
| `/keel:backlog <befehl>` | PO, Auditor | Backlog über die Schnittstelle: next, show, list, propose, status, link; Anbieter Markdown oder GitHub Issues |

Vorlagen entscheidet tagsüber der Supervisor innerhalb seiner Stufe; richtungsweisende reichen bis zum Menschen und werden im Morgen-Briefing entschieden. Unbeaufsichtigte Läufe: `scripts/keel-run.sh <projekt> "/keel:vorhaben <name>"` wartet Nutzungslimits ab und meldet sich, wenn ein Briefing nötig ist. Der Supervisor läuft auf Fable (Claude Code ab 2.1.251).

## Ein Vorhaben durchführen

Der Mensch schreibt drei Sätze ins Backlog: Titel, Problem, Warum. Dann in einer Claude-Code-Session im Projekt:

```
/keel:vorhaben <name> <backlog-id>
```

Die Haupt-Session ist der Lead. Der PO macht aus dem Backlog-Element eine Problemstellung mit Pflicht-, verhandelbaren und Akzeptanzkriterien, der Architekt bewertet sie in drei Stufen mit Kosten, der PO entscheidet den Kompromiss innerhalb seiner Befugnisse oder legt vor. Dann ruft der Lead der Reihe nach Tester (Abnahmetests), Planer und je Aufgabe Tester, Entwickler und Reviewer als Subagents auf. Hooks prüfen jede Übergabe an der Grenze über das Frontmatter der Dateien unter `.keel/work/`, zählen das Budget pro Rolle, schützen die Tests des Testers vor dem Entwickler und lassen das Prüftor beim Beenden des Entwicklers laufen. Die Arbeit läuft auf `feature/<name>`, abgezweigt vom Basis-Branch aus `.keel/config.yaml` (`git.base_branch`, etwa `develop` oder `staging`). Am Ende steht ein Abnahmenachweis unter `.keel/work/acceptance/`. Nimmt der PO ab (`status: abgenommen`), integriert der nächste Aufruf in die Basis: Merge, Abnahmetests in die Regressionssuite, Branch weg. Der Weg von der Basis nach `main` bleibt ein manueller Schritt. Ob eine Aufgabe das Review besteht, rechnet ein Hook gegen eine Schwelle; jede Nacharbeit wird als eigenes Delta erneut reviewt, weitere Runden gibt es nur, solange die Befunde sinken, sonst entscheidet der Supervisor. Anmerkungen unter der Schwelle sammelt die Pflegeliste, die der Architekt wöchentlich zu Prüfregeln oder gebündelten Pflegeaufgaben macht (System-ADR 0018). Bei Testeinspruch oder erschöpftem Budget schneidet der Planer die Aufgabe neu: an Ort und Stelle, ersetzt durch kleinere, oder verworfen. Erst beim zweiten Neuschnitt derselben Aufgabe schreibt der Lead eine Vorlage und das Vorhaben bleibt `blockiert`, bis ein Mensch entscheidet.

Rohdaten für die Lernschleife landen außerhalb des Repos unter `~/.keel-metrics/<projekt>-<hash>/` (`bin/keel path runtime` nennt den Ordner).

`bin/keel doctor` prüft, ob Projekt und Rechner für keel taugen: Python, `git`, `jq`, Konfiguration, lesbare Frontmatter aller Artefakte, Notbremse, verwaiste Startmarken, Protokolle, Sperrordner. `/keel:hilfe` und der Monitor zeigen dieselben Befunde.

## Installation in einem Projekt

Voraussetzungen: `git`, `python3` (ab 3.9, nur Standardbibliothek) und `jq`. Auf macOS kommen `git` und `python3` mit den Command Line Tools (`xcode-select --install`), `jq` liegt ab macOS 15 unter `/usr/bin/jq`, auf älteren Versionen über Homebrew. Auf Linux kommen alle drei aus der Paketverwaltung. Fehlt `jq` oder `python3`, blockieren die keel-Hooks, statt ungeprüft durchzulassen (System-ADR 0019).

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

## Mitarbeit

Einmal pro Klon die Hooks einschalten und eine Identität setzen, die nichts Privates verrät: den GitHub-Login und die noreply-Adresse aus den GitHub-Einstellungen unter Emails.

```bash
git config core.hooksPath .githooks
git config user.name <login>
git config user.email <id>+<login>@users.noreply.github.com
```

`pre-commit` und `pre-push` prüfen mit `tests/leak_check.py` Identität, Home-Pfade, E-Mail-Adressen und Secrets; dieselbe Prüfung läuft in der CI bei jedem PR. Eigene Begriffe, die nie öffentlich werden sollen, gehören in `~/.config/keel/leak-denylist` (ein regulärer Ausdruck pro Zeile), nie ins Repo. Sicherheitslücken bitte nach `SECURITY.md` melden.

## Stand

Alle Rollen des Konzepts sind gebaut und im Beispielprojekt erprobt, dazu die Epic-Ebene für große Themen. Der Mensch schreibt Backlog-Einträge, entscheidet Vorlagen und die Reihenfolge, pflegt die Maßstab-Dateien. Offen: Linear-Adapter, Basisregel-Pakete pro Sprache, Einsatz in einem bestehenden Projekt mit Bestandsaufnahme.

## Lizenz

MIT, siehe `LICENSE`.
