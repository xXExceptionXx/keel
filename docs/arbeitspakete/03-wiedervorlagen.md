# Arbeitspaket 3: Wiedervorlagen und klare Entscheidungswege

2026-10-01 · Grundlage: Coach-Bericht und Briefing vom 2026-10-01 im Beispielprojekt (Projekt-ADRs 0022 und 0023, Abschnitte „Umzusetzen im keel-Repo“), dazu die Nachschärfung von ADR 0022 aus der Auswertung des Briefings. Zum Planen im Plan-Modus, dann Umsetzung auf einem eigenen Branch.

**Stand 2026-10-02: umgesetzt** auf `feature/wiedervorlagen`, System-ADR 0021, Version 0.16.0. Abweichungen von diesem Entwurf: Motor-Vorschläge und Motor-Befunde gehen nicht als GitHub-Issue in das inzwischen öffentliche Plugin-Repo, sondern in die lokale Motor-Ablage `~/.keel-metrics/motor/` (`keel motor`); `.keel/motor-vorschlaege/` und `motor.repo` entfallen. Eine Coach-Vorlage mit `ebene: motor` sperrt nicht, sie steht bis zum Weiterreichen auf der Tagesordnung. Eine Wiedervorlage, die mehr als sieben Tage über ihrem Termin liegt, sperrt wieder. Das Briefing bleibt auf dem ausgecheckten Branch; ADRs entstehen dort als Entwurf. Teil G (Übergang im Beispielprojekt) entfällt, das Beispielprojekt ist gelöscht.

## Ausgangslage

Der erste Probelauf mit 0.14.0 und Opus 5.5 hat zwei Lücken im Entscheidungsweg sichtbar gemacht:

1. **Offene Fragen gehen verloren.** Der Coach hat 13 Punkte gezählt, die auf eine Entscheidung warten und die niemand abfragt: zehn geroutete Audit-Befunde seit neun Tagen auf `vorgeschlagen`, zwei im Briefing zurückgestellte Punkte, die nur im Protokoll stehen, und ein ADR auf `Proposed` mit `entscheider: Supervisor`, auf dem ein Vorhaben schon integriert ist. `briefing_needed.py` sieht keinen davon.
2. **Es gibt nur „sperrt alles“ oder „unsichtbar“.** Jede offene Vorlage macht das Briefing hart fällig und hält alle Rollen an. Ein Zurückstellen kennt der Motor nicht: Die im Briefing bewusst offen gelassene Vorlage zum Einwand-Korridor sperrt das Beispielprojekt seitdem.

Dazu zwei Entscheidungen des Menschen aus dem Briefing, die den Motor betreffen: Projekt-ADR 0022 (offene Fragen brauchen einen Träger, den ein Skript sieht) und Projekt-ADR 0023 (das Zeitbudget meldet nur noch).

## Begriffe

- **Vorlage:** eine Entscheidung, die ansteht. Sperrt die Rollen, bis sie entschieden ist, wie heute.
- **Wiedervorlage:** ein offener Punkt, der zu einem Termin oder im nächsten Briefing wiederkommt. Sperrt nicht. Sie ist der Träger einer offenen Frage: eine Stelle, die ein Skript sieht, sodass die Frage nicht vergessen werden kann.

Im Code heißt die Wiedervorlage `followup` (Typ) mit `due` (Termin); in Artefakten, Prompts und Doku „Wiedervorlage“.

## Ziel

Jede offene Frage hat genau einen Ort, den ein Skript sieht, und Fragen zum Motor verlassen das Projekt in einen eigenen Entscheidungsweg. Was eine Weichenstellung ist, sperrt; was nur auf die Tagesordnung gehört, kommt wieder, ohne die Arbeit anzuhalten. Fehlentscheidungen auf der falschen Stufe werden an der Quelle verhindert, nicht erst später gesucht.

## Umfang

### A. Zeitbudget meldet nur noch (Projekt-ADR 0023)

- `hooks/tool-gate.sh`: Beim Überschreiten der Minuten kein `deny` und kein `budget_exhausted` mehr, stattdessen einmal je Lauf das Ereignis `budget_slow` (Rolle, Agent, Bezug, Minuten). Ein Merker hält die Einmaligkeit; die Ausnahme für `.keel/work/` entfällt.
- `hooks/agent-stop.sh`: Die `.timeout`-Bedingung fällt aus der Budget-Prüfung beim Ende; der neue Merker wird aufgeräumt.
- `scripts/lage.py` und Monitor: ein langsamer Lauf ist ein Hinweis, kein Sperrzustand.
- `scripts/metrics.py`: `budget_slow` zählt nicht in „Budgetverstöße“, sondern als eigene Zeile ohne Korridor.
- Konfigurationsvorlage: `minutes` und `architekt_minutes` bleiben, beschrieben als Meldeschwelle.
- Texte in Skills und Rollen, die „Zeitbudget erschöpft“ als Sperre beschreiben.
- Vertragstest: Ein Lauf über der Schwelle erzeugt genau ein `budget_slow` und keine Ablehnung. Damit ist belegt, dass die Meldung auslöst (die Regel des Coaches aus dem Kontext-Alarm).

### B. Zwei Stufen: Vorlage und Wiedervorlage (Projekt-ADR 0022, nachgeschärft)

- **Ablage:** `.keel/decisions/wiedervorlagen/<datum>-<slug>.md` mit Frontmatter `typ: wiedervorlage`, `titel`, `frage`, `quelle` (Briefing, Vorlage, Coach …), `faellig` (Datum, optional), `status: offen | erledigt`, `ergebnis`.
- **`briefing_needed.py`** liefert künftig zwei Listen:
  - `gruende`: sperrend, wie heute (Supervisor-ADRs mit `vorgelegt: offen`, eskalierte Vorlagen, Coach-Vorlagen, Epics in `kurskorrektur`).
  - `tagesordnung`: nicht sperrend (fällige oder terminlose Wiedervorlagen, dazu die abgeleiteten Punkte aus C).
  - Exit 1 nur bei sperrenden Gründen; der Vertrag aus System-ADR 0019 bleibt.
- **`due.py`:** Das Briefing ist hart fällig nur bei sperrenden Gründen. Eine nicht leere Tagesordnung ist ein weicher Hinweis („n Punkte für das nächste Briefing“).
- **Zurückstellen:** Stellt der Mensch eine Vorlage im Briefing zurück, setzt der Supervisor `status: zurueckgestellt` und legt eine Wiedervorlage mit Termin an, die auf die Vorlage verweist. Eine zurückgestellte Vorlage sperrt nicht; ist ihre Wiedervorlage fällig, steht sie wieder auf der Tagesordnung. Erreicht sie zum zweiten Mal den Termin, wird sie wieder zur sperrenden Vorlage, damit nichts endlos vertagt wird.
- **Briefing-Skill:** erst Vorlagen (sperrend), dann die Tagesordnung, Wiedervorlagen je Punkt mit kurzer Frage. Neue Regel: Jeder Punkt, der im Briefing offen bleibt, wird vor dem Ende eine Wiedervorlage; ein Vermerk nur im Protokoll ist nicht erlaubt (ein Hook prüft beim Ende des Briefings, dass das Protokoll keine offenen Punkte ohne Wiedervorlage nennt, soweit das prüfbar ist).

### C. Abgeleitete Tagesordnung, ohne eigene Datei

Was sich aus dem Zustand berechnen lässt, braucht keine Wiedervorlage-Datei; `briefing_needed.py` leitet es bei jedem Aufruf ab:
- Backlog-Elemente mit `Herkunft: Audit`, die länger als zwei Tage auf `vorgeschlagen` stehen. Gelesen über die Backlog-Schnittstelle, damit der GitHub-Anbieter mitläuft; `route_findings.py` schreibt dafür ein Datum an das Element.
- ADRs mit `status: Proposed` auf dem Basis-Branch.

### D. Falsche Stufe an der Quelle verhindern

- **Beim Ende einer Rolle** (`agent-stop.sh`): Legt eine Rolle, die nicht Supervisor ist, ein ADR mit `entscheider: Supervisor` oder `entscheider: Mensch` an oder ändert diese Felder, wird das Ende abgelehnt: „Lege eine Vorlage an, statt ein ADR auf fremder Stufe zu schreiben.“ Deterministisch über den Diff von `.keel/adr/`.
- **Bei der Integration:** Ein Vorhaben wird nicht integriert, solange auf seinem Branch ein ADR auf `status: Proposed` liegt. Die Prüfung ist ein Skript, das der Ablauf in `skills/vorhaben/SKILL.md` vor dem Merge aufruft, mit Vertragstest.

### E. Kennzahlen bleiben ehrlich

- Wiedervorlagen zählen weder als Eskalation noch als Vorlage an den Menschen. `metrics.py` bekommt eine eigene Zeile „offene Wiedervorlagen“ und „älteste Wiedervorlage in Tagen“, ohne Korridor im ersten Schritt.
- Die Kennzahl „Einwände des Supervisors“ bleibt unverändert; ihre Vorlage ist im Beispielprojekt noch offen und wird vom Menschen entschieden.

### F. ADR-Nummern ohne Kollision zwischen Branches

- Heute vergibt jede Rolle auf ihrem Branch die nächste freie Nummer; im Beispielprojekt liegt 0021 auf dem V6-Branch, und das Briefing auf dem Basis-Branch musste 0022 und 0023 nehmen.
- Vorschlag: Auf Feature-Branches entstehen ADR-Entwürfe ohne Nummer (`entwurf-<slug>.md`, `nummer: offen`). Die Nummer vergibt ein Skript bei der Integration auf dem Basis-Branch; Verweise im Vorhaben werden dabei nachgezogen. Auf dem Basis-Branch selbst (Briefing, Supervisor) wird wie bisher direkt nummeriert.

### G. Übergang im Beispielprojekt

Nicht Teil des Motors, aber nach dem Einspielen nötig und im PR zu beschreiben: Die zwei Träger-Vorlagen, die der Supervisor im Briefing vom 2026-10-01 angelegt hat (`2026-10-01-briefing-audit-backlog-bereit-oder-verworfen.md`, `2026-10-01-briefing-zielbild-laufzeit-und-leitlinien-kandidaten.md`), werden im nächsten Briefing in Wiedervorlagen überführt. Das entscheidet der Mensch dort, nicht der Motor.

### I. Motor-Vorschläge vom Projekt trennen

Heute schreibt der Coach jeden Vorschlag als Vorlage ins Projekt, und das Briefing macht daraus ein Projekt-ADR, auch wenn die Änderung Hooks, Skripte oder Rollen des Plugins betrifft. Eine Brücke ins keel-Repo gibt es nicht; im Probelauf wurden die Abschnitte „Umzusetzen im keel-Repo“ von Hand übertragen. Folgen: Motor-Entscheidungen landen in der Projekt-Historie, mehrere Projekte können denselben Motor unterschiedlich entscheiden, angenommene Justierungen versanden, und eine Motor-Frage sperrt die Arbeit im Projekt.

- **Ebene je Vorschlag.** Der Coach setzt im Frontmatter jeder Vorlage `ebene: projekt | motor`, nach fester Regel: `projekt` für alles unter `.keel/` (Korridorwerte der Projektkonfiguration, Projektregeln, Leitlinien), `motor` für alles im Plugin (Hooks, Skripte, Skills, Rollen, Standardwerte, Vorlagen). Ein Vorschlag, der beides betrifft, wird geteilt. `agent-stop.sh` prüft beim Ende des Coaches, dass das Feld gesetzt ist.
- **Projekt-Vorschläge** laufen wie heute: Vorlage, Briefing, Projekt-ADR, Umsetzung im Projekt.
- **Motor-Vorschläge** werden im Briefing nur weitergereicht oder verworfen, nicht entschieden. Bei „weiterreichen“ legt der Supervisor nach dem Ja des Menschen ein Issue im Motor-Repo an (`motor.repo`, Label `coach-vorschlag`): Problem, Optionen, Empfehlung, Hypothese, die belegenden Kennzahlen, Projektname und Plugin-Version, aber kein Code und keine Inhalte aus dem Projekt. Die Vorlage im Projekt wird mit `status: weitergereicht` und dem Link auf das Issue abgeschlossen und sperrt nicht mehr. Ein Projekt-ADR entsteht nicht.
- **Im keel-Repo** entscheidet der Mensch einmal für alle Projekte, mit System-ADR und Hypothese. Gleiche Vorschläge aus mehreren Projekten werden im Issue zusammengeführt; das System-ADR verweist auf alle.
- **Rückweg über die Version.** Kommt eine angenommene Justierung mit einer neuen Plugin-Version ins Projekt, prüft der Coach ihre Hypothese ab dieser Version; er liest die System-ADRs des Plugins schon heute. Ein weitergereichter Vorschlag, der nach einer festen Frist (Vorschlag: 30 Tage) weder umgesetzt noch abgelehnt ist, erscheint als Wiedervorlage im Briefing des Projekts, damit er nicht versandet.
- **Kanal ohne GitHub.** Ist `gh` nicht verfügbar oder `motor.repo` nicht gesetzt, legt der Supervisor eine Datei unter `.keel/motor-vorschlaege/` ab und nennt den Pfad; die Vorlage wird trotzdem abgeschlossen.
- **Coach und Briefing:** Rollen- und Skill-Texte für Coach, Supervisor und `/keel:briefing`; `/keel:hilfe` behält seinen Kanal für Motor-Befunde (Fehler), der Coach-Kanal ist für Vorschläge.

### H. Tests und Doku

- Vertragstests für: Coach-Vorlage ohne `ebene` wird beim Ende abgelehnt; weitergereichte Motor-Vorlage sperrt nicht und erzeugt kein Projekt-ADR; Rückkehr als Wiedervorlage nach Ablauf der Frist; Ablage unter `.keel/motor-vorschlaege/` ohne `gh`; `budget_slow` ohne Ablehnung; Tagesordnung ohne Sperre; Zurückstellen ohne Sperre und Rückkehr zur Sperre beim zweiten Termin; abgeleitete Punkte aus Backlog und `Proposed`-ADRs; Ablehnung eines ADR auf fremder Stufe; Integrationsprüfung; Kennzahlen ohne Wiedervorlagen in der Eskalationsquote; Vergabe der ADR-Nummer bei der Integration.
- System-ADR mit der nächsten freien Nummer, mit den Hypothesen aus Projekt-ADR 0022 und 0023. Ergänzung in `docs/system.md` (Briefing und Fälligkeiten), Notiz in `docs/konzept.md`, Rollen- und Skill-Texte für Supervisor, Coach und Lead.

## Nicht im Umfang

- Die Entscheidung über den Einwand-Korridor. Sie liegt beim Menschen im Briefing des Beispielprojekts.
- Das vollständige Entfernen des Zeitbudgets. Laut Projekt-ADR 0023 eine spätere, eigene Entscheidung, wenn die Meldung belegt nie auslöst.
- Ein Werkzeug, das Motor-Vorschläge mehrerer Projekte automatisch zusammenführt. Zunächst geschieht das von Hand im Issue.
- Ein generierter ADR-Index in `.keel/CLAUDE.md`. Der Coach hat ihn zurückgestellt, bis der nächste Prüfbericht zeigt, ob die Klasse weiterlebt.

## Abnahme

- Eine Wiedervorlage erscheint im Briefing und sperrt keine Rolle; eine Vorlage sperrt wie bisher.
- Eine im Briefing zurückgestellte Vorlage sperrt nicht, kommt zum Termin wieder und sperrt beim zweiten Erreichen des Termins.
- Ein Audit-Element, das drei Tage auf `vorgeschlagen` steht, und ein `Proposed`-ADR auf dem Basis-Branch stehen auf der Tagesordnung, ohne dass jemand eine Datei anlegt.
- Eine Arbeitsrolle, die ein ADR mit `entscheider: Supervisor` schreibt, kann nicht enden; eine Integration mit `Proposed`-ADR auf dem Branch bricht mit Meldung ab.
- Ein Lauf über der Minutengrenze erzeugt genau ein `budget_slow` und keine Ablehnung.
- Eskalationsquote und Vorlagen pro Woche ändern sich nicht, wenn Wiedervorlagen dazukommen.
- Ein ADR-Entwurf auf einem Feature-Branch bekommt seine Nummer erst bei der Integration, ohne Kollision.
- Eine Motor-Vorlage des Coaches führt nach dem Weiterreichen zu einem Issue im Motor-Repo (oder einer Datei ohne `gh`), schließt im Projekt ohne Projekt-ADR ab und sperrt keine Rolle; eine Projekt-Vorlage läuft unverändert.
- Alle Vertragstests aus Arbeitspaket 1 und 2 grün, CI grün.

## Abhängigkeiten und Reihenfolge

- Paket 3 berührt `briefing_needed.py`, `due.py`, `metrics.py`, `lage.py` und die Hooks, also genau die Dateien, die Paket 2 auf die neue Ablage umstellt. Empfohlen: **erst Paket 2, dann Paket 3**, damit nicht dieselben Stellen zweimal angefasst werden.
- Paket 2 ist umgesetzt (PR #13, System-ADR 0020). Paket 3 baut darauf auf: Frontmatter, Konfiguration, Ereignisse und Schreibzugriffe laufen über `lib/keel/store` (`frontmatter.fields`/`update`, `config.get`, `events.read`/`append`, `io.atomic_write`/`file_lock`), neue Schlüssel kommen ins Schema in `store/config.py` und ins Template, und `tests/unit/test_legacy_patterns.py` muss grün bleiben. Neue Fristen und Datumsvergleiche nutzen `events.parse_ts` (UTC); ein Kalendertag beginnt um lokale Mitternacht wie in `due.py`.
- Ausnahme, falls das Beispielprojekt dringend weiterlaufen soll: Teil A (Zeitbudget) ist klein und unabhängig und kann vorgezogen werden.
- Die nachfolgenden Pakete aus `02-kern-fundament.md` verschieben sich um eins: Hook-Dispatcher wird Paket 4, Messung Paket 5, Rollenkern Paket 6, Graph Paket 7.

## Entscheidungen, die beim Planen fallen

- **Kanal für Motor-Vorschläge:** GitHub-Issue im Motor-Repo (Vorschlag) oder eine gemeinsame Ablage außerhalb der Projekte? Und: Legt der Supervisor das Issue im Briefing an (nach dem Ja des Menschen) oder erst `/keel:hilfe` auf Nachfrage?
- **Frist bis zur Wiedervorlage** eines weitergereichten Vorschlags: 30 Tage oder an die nächste Plugin-Version gekoppelt?

- **Ablageort der Wiedervorlagen:** eigener Ordner unter `.keel/decisions/` (Vorschlag) oder Abschnitt in einer Datei?
- **Zweiter Termin sperrt:** Ist „zweimal vertagt wird wieder sperrend“ die richtige Grenze, oder soll der Mensch einen Punkt ausdrücklich dauerhaft ohne Sperre parken können?
- **Prüfung im Briefing-Protokoll:** Lässt sich „kein offener Punkt ohne Wiedervorlage“ deterministisch prüfen (etwa über einen festen Abschnitt `## Zurückgestellt` mit Verweisen), oder bleibt es eine Regel im Skill?
- **ADR-Nummern:** Entwürfe ohne Nummer mit Vergabe bei der Integration (Vorschlag) oder eine zentrale Vergabe auf dem Basis-Branch schon beim Anlegen?
- **System-ADR und Version:** Paket 2 ist System-ADR 0020 mit 0.15.0, Paket 3 wird damit System-ADR 0021 mit 0.16.0 (vor dem Anlegen `origin/main` holen und die Nummer prüfen).
