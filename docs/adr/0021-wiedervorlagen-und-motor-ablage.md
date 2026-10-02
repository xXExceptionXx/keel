---
nummer: 0021
titel: Wiedervorlagen statt Sperre oder Vergessen, ADR-Stufen an der Quelle, ADR-Nummern bei der Integration, lokale Motor-Ablage
status: Accepted
datum: 2026-10-02
entscheider: Ich
supersedes:
hypothese: In vier Wochen Betrieb steht kein offener Punkt nur in einem Briefing-Protokoll (briefing_protokoll_offen bleibt 0); budget_slow löst mindestens einmal aus und kein Rollenlauf wird wegen Zeit abgelehnt; es gibt keine ADR-Nummernkollision zwischen Branches und kein ADR auf fremder Stufe; Eskalationsquote und Vorlagen pro Woche bleiben in ihren Korridoren, obwohl Wiedervorlagen dazukommen; kein Motor-Vorschlag und kein Motor-Befund erreicht das öffentliche Plugin-Repo als Issue
---

# 0021: Wiedervorlagen statt Sperre oder Vergessen, ADR-Stufen an der Quelle, ADR-Nummern bei der Integration, lokale Motor-Ablage

## Kontext

Der erste Probelauf mit 0.14.0 hat zwei Lücken im Entscheidungsweg gezeigt. Der Coach zählte 13 offene Fragen, die kein Skript sah: geroutete Audit-Befunde seit Tagen auf `vorgeschlagen`, im Briefing zurückgestellte Punkte, die nur im Protokoll standen, ein ADR auf `Proposed`, auf dem schon gebaut war. Und es gab nur zwei Zustände: Eine offene Vorlage sperrte alle Rollen, alles andere war unsichtbar. Eine im Briefing bewusst offen gelassene Vorlage hielt das Beispielprojekt danach an.

Dazu kamen drei weitere Befunde. ADR-Nummern kollidierten, weil jede Rolle auf ihrem Branch die nächste freie Nummer nahm. Rollen konnten ADRs mit `entscheider: Supervisor` schreiben. Vorschläge des Coachs zum Plugin selbst wurden als Projekt-ADR entschieden, obwohl sie alle Projekte betreffen. Das Zeitbudget lehnte Werkzeugaufrufe ab, obwohl der Mensch im Briefing entschieden hatte, dass es nur melden soll (Projekt-ADRs 0022 und 0023 des Beispielprojekts).

Seit dem 2026-10-02 ist das Plugin-Repo öffentlich. Motor-Befunde von `/keel:hilfe` gingen bis dahin als GitHub-Issue dorthin (System-ADR 0014), und Arbeitspaket 3 sah denselben Weg für Motor-Vorschläge vor. Ein Issue aus einem Projekt kann Pfade, Namen und Kennzahlen enthalten, die nicht öffentlich werden dürfen.

## Entscheidung

**Zeitbudget meldet nur.** Ein Lauf über `budget.minutes` schreibt einmal `budget_slow` und wird nicht abgelehnt. Das Aufrufbudget sperrt weiter und schreibt weiter `budget_exhausted`.

**Zwei Stufen: Vorlage und Wiedervorlage.** Eine Wiedervorlage liegt unter `.keel/decisions/wiedervorlagen/` (Frontmatter `typ: wiedervorlage`, `frage`, `quelle`, `faellig`, `status`, optional `vorlage` und `runde`) und wird nur mit `wiedervorlage.py neu` angelegt. `briefing_needed.py` liefert neben den sperrenden Gründen eine Tagesordnung, die nie sperrt: fällige Wiedervorlagen, zurückgestellte Vorlagen in Runde 1, Audit-Vorschläge, die länger als zwei Tage warten, `Proposed`-ADRs auf der Basis und Motor-Vorschläge. Eine zurückgestellte Vorlage sperrt nicht und kommt zum Termin wieder; beim zweiten Termin (`runde: 2`) sperrt sie wieder. Eine Wiedervorlage, die mehr als `faelligkeiten.wiedervorlage_ueberfaellig_tage` (7) über ihrem Termin liegt, sperrt ebenfalls. Eine zurückgestellte Vorlage ohne offene Wiedervorlage sperrt, damit nichts verloren geht. Exit-Codes und `briefing_noetig` bleiben, alle Aufrufer laufen unverändert.

**Das Briefing endet ohne offene Punkte im Protokoll.** `skill-gate.sh` hält beim Start des Briefings dessen Stand fest. Ein neuer Stop-Hook prüft, sobald seit dem Start ein Protokoll geschrieben wurde: Abschnitt `## Zurückgestellt` vorhanden, jeder Eintrag zeigt auf eine offene Wiedervorlage mit Termin nach heute, jeder sperrende Grund vom Start ist entschieden oder zurückgestellt, jede neu zurückgestellte Vorlage und jede fällige Wiedervorlage ist erledigt oder dort genannt. Ein Befund blockiert das Ende mit den Gründen, höchstens dreimal; danach lässt der Hook los und schreibt `briefing_protokoll_offen`. Der Hook ist ein Beobachter: Ein interner Fehler hält die Session nie fest. Das Briefing bleibt auf dem ausgecheckten Branch, weil dort die Punkte liegen, die die Rollen sperren.

**ADRs nur auf der eigenen Stufe.** `agent-gate.sh` hält beim Start einer Rolle den ADR-Stand fest (Prüfsumme, `entscheider`, `status`), `agent-stop.sh` vergleicht beim Ende. Planer und Architekt schlagen nur vor (`Proposed`, ohne Entscheider), der PO entscheidet auf seiner Stufe, der Supervisor nie für den Menschen, alle anderen Rollen ändern keine ADRs. Keine Rolle außer dem Supervisor fasst eine Datei auf Stufe Supervisor oder Mensch an. Fehlt der Stand, ist das ein Fehler (fail closed). Unter `.keel/adr/` darf eine Rolle auch über dem Aufrufbudget schreiben, damit sie Abgelehntes reparieren kann.

**ADR-Nummern bei der Integration.** `adr.py neu` legt auf der Basis ein nummeriertes ADR an, auf jedem anderen Branch einen Entwurf `entwurf-<slug>.md` mit `nummer: offen`. Vor der Integration lehnt `adr.py check-integration` einen Branch mit `Proposed`-Entwurf oder neuer nummerierter Datei ab. Integriert wird mit `merge --no-commit`, `adr.py number` und einem Commit: Die Entwürfe bekommen die nächsten freien Nummern, Verweise unter `.keel/` (Plan, Epic-`leitentscheidungen`, Index in `.keel/CLAUDE.md`, `supersedes`) werden vorher umgeschrieben. Das gilt auch für den Supervisor und für Briefings auf einem Feature-Branch. Wird ein Vorhaben verworfen, listet `wiedervorlage.py list --nur-branch` zuerst die offenen Punkte, die es nur auf seinem Branch gibt.

**Lokale Motor-Ablage statt Issues.** Vorschläge des Coachs und Befunde von `/keel:hilfe`, die das Plugin betreffen, gehen nach `~/.keel-metrics/motor/` (`keel motor add|list|show|set`), nicht in das öffentliche Repo. Ein Eintrag nennt sein Projekt nur mit dem Laufzeit-Schlüssel, trägt die Plugin-Version und keinen Code. `keel motor add` lehnt Text mit Secrets, Home-Pfaden, fremden Adressen, Begriffen der privaten Sperrliste oder den `compliance.pii_patterns` des Projekts ab und nennt nur die Gründe. Der Coach setzt je Vorlage `ebene: projekt | motor`; ein Hook lehnt sein Ende ohne gültige Ebene ab. Motor-Vorlagen sperren nicht, im Briefing werden sie weitergereicht oder verworfen, ohne Projekt-ADR; nach 30 Tagen ohne Entscheidung im keel-Repo kommen sie auf die Tagesordnung zurück. `motor.repo` entfällt. Dieser Teil ersetzt den Issue-Kanal aus System-ADR 0014.

## Verworfen

- **Git-Diff gegen HEAD für die Stufenprüfung.** `.keel/` wird nur an bestimmten Punkten committet; ein Diff hätte frühere Rollen beschuldigt.
- **Zentrale Nummernvergabe beim Anlegen.** Verworfene Vorhaben hinterlassen Lücken, und die Vergabe bräuchte einen gemeinsamen Zustand außerhalb des Repos.
- **GitHub-Issues als Motor-Kanal.** Das Plugin-Repo ist öffentlich; Projektinterna gehören nicht dorthin.
- **Protokollprüfung bei jedem Zug.** Das Briefing ist ein Gespräch; geprüft wird erst, wenn ein Protokoll existiert.
- **Wechsel des Briefings auf die Basis.** Er hätte genau die Vorlagen ausgeblendet, die auf dem Feature-Branch die Rollen sperren.
- **Dauerhaft parken ohne zweiten Termin.** Was zweimal vertagt wurde, sperrt wieder.

## Folgen

- Eine offene Frage hat genau einen Ort, den ein Skript sieht; das Protokoll allein reicht nicht mehr.
- Fehlt der ADR-Stand eines Rollenlaufs, etwa weil das Plugin während des Laufs aktualisiert wurde, scheitert das Ende, und nach drei Versuchen greift die Notbremse aus System-ADR 0019.
- Ein `Proposed`-Entwurf hält die Integration an, bis er entschieden ist.
- Audit-Vorschläge aus einem GitHub-Backlog erscheinen nur mit `briefing_needed.py --voll` auf der Tagesordnung; die Hooks bleiben ohne Netzwerk.
- Der Stop-Hook läuft nach jedem Zug jeder Session in einem Projekt mit `.keel/`, prüft aber nur, wenn ein Briefing-Marker existiert.
- Was aus der Motor-Ablage ins keel-Repo übernommen wird, prüft dort der Leak-Check bei Commit und Push.
