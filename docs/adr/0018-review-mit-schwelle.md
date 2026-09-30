---
nummer: 0018
titel: Review mit Schwelle, Nacharbeit wird erneut reviewt, Anmerkungen gehen in eine Pflegeliste
status: Accepted
datum: 2026-09-30
entscheider: Ich
supersedes:
hypothese: Fehler, die eine Nacharbeit einbaut, erreichen keinen Commit mehr unerkannt; „Nacharbeitsrunden mit neuen Befunden aus der Nacharbeit“ wird messbar und liegt nach vier Wochen im Korridor 0–20 %; der Anteil verfallener Pflege-Anmerkungen bleibt unter 50 %, sonst sind Anmerkungen Rauschen oder das Pflegebudget ist zu klein
---

# 0018: Review mit Schwelle, Nacharbeit wird erneut reviewt, Anmerkungen gehen in eine Pflegeliste

## Kontext

Beobachtung aus dem Betrieb: Fixes nach einem Review bauen oft selbst Fehler ein. Weil die Befunde als behoben gelten, gehen diese Fehler ohne echtes Review durch. keel hatte zwar eine zweite Review-Runde, sie hatte aber drei Lücken:

1. **Herabstufung in Runde 2.** Neue Befunde durften nur blockierend sein, alles andere wurde zur Anmerkung. Ein *wichtiger* Fehler aus dem Fix hat die Aufgabe also nicht aufgehalten.
2. **Der Fix war nicht sichtbar.** Der Reviewer sah `git diff HEAD`, also den gesamten Stand, und hakte in Runde 2 die Befunde der Vorrunde ab. Was die Nacharbeit zusätzlich verändert hatte, ging darin unter. Neue, ungetrackte Dateien, etwa die Tests des Testers, fehlten in diesem Diff ganz.
3. **„Bestanden“ war ein Urteil.** Der Reviewer setzte den Status selbst, und der Hook prüfte nur, dass es ihn gab.

Dazu kam die feste Grenze von zwei Runden aus dem Konzept. Die Regel für Runde 2 hatte einen guten Grund: Ein frischer Reviewer findet in jeder Runde neue Kleinigkeiten, und die Schleife endet nie. Diesen Schutz behält die Entscheidung, sie fasst ihn aber genauer.

Die zweite Beobachtung: Anmerkungen unter der Schwelle blieben für immer liegen. Damit verschenkt keel die Chance, den Code nachhaltig auf einem guten Niveau zu halten.

## Entscheidung

**Review mit Schwelle.** Eine Umsetzung gilt erst als umgesetzt, wenn keine Zahl über ihrer Schwelle liegt (`review.schwelle_blockierend`, `review.schwelle_wichtig`, Standard 0). Der Reviewer schreibt die Anzahl je Schweregrad ins Frontmatter. `scripts/review.py pruefen` rechnet im Stop-Hook nach: Zahlen gegen Tabelle, Herkunft gegen Runde, Status gegen Schwelle. Stimmt etwas nicht, wird die Übergabe abgelehnt. Die Schweregrade hängen an Kriterien: blockierend heißt, ein Kriterium oder ADR ist verletzt oder der Nachweis stimmt nicht; wichtig heißt, ein Kriterium ist teilweise erfüllt, ungetestet oder weicht vom Referenzbeispiel ab; Anmerkungen haben keinen Kriterienbezug.

**Jede Runde reviewt die Nacharbeit als eigenes Delta.** Beim Start des Reviewers hält das Gate den Stand als Git-Tree fest (`review_stand_r<n>`, einschließlich ungetrackter Dateien, ohne den echten Index anzufassen). `review.py diff` zeigt dem Reviewer den gesamten Stand, `review.py diff --runde` das Delta der Nacharbeit. Jeder Befund trägt eine Herkunft:

- **neu:** Runde 1
- **offen:** aus der Vorrunde, nicht behoben
- **fix:** neu, im Delta der Nacharbeit; zählt mit vollem Schweregrad
- **bestand:** neu, in Code, den die Nacharbeit nicht angefasst hat; nur blockierend oder Anmerkung. Das ist der alte Schutz gegen endlose Runden.

**Konvergenz statt fester Rundenzahl.** Der Hook schreibt `review_ergebnis` in die Aufgabe, der Lead liest nur das:

- **bestanden:** unter der Schwelle
- **nacharbeit:** Runde 1, oder die Befunde sinken, das heißt (blockierend, wichtig) ist lexikografisch kleiner als in der Vorrunde. Beispiel: 4 blockierend → 2 wichtig → 2 Anmerkungen → bestanden.
- **vorlage:** Die Befunde sinken nicht, oder `review.max_runden` (Standard 4) ist erreicht.

Die Vorlage geht an den Supervisor. Er kann die Aufgabe in den Neuschnitt geben, eine weitere Runde erlauben (`review_zusatzrunden`), sie verwerfen oder an den Menschen eskalieren. Ein Neuschnitt ohne Vorlage nach Runde 2 entfällt.

**Anmerkungen gehen in eine Pflegeliste.** Aus einem bestandenen Review sammelt der Stop-Hook die Anmerkungen nach `.keel/work/pflege.md` (`scripts/pflege.py`). Der Architekt sichtet die Liste in der Wochenrunde, weil Anmerkungen Strukturfragen sind und keine Produktfragen:

1. **Regel vor Aufgabe:** Ein wiederkehrendes Muster wird Prüfregel in `.keel/architektur.md`. Damit wertet der Reviewer es künftig als Abweichung, und das Problem wird an der Quelle behoben statt immer wieder nachgebessert.
2. **Bündeln:** Was sich lohnt, wird zur Pflegeaufgabe (`wird Pflege`). Sie wird am Tagesstart als Backlog-Vorschlag mit Herkunft Pflege geroutet. Ob sie eingeplant wird, entscheidet der Mensch im Backlog.
3. **Verwerfen** mit Grund.
4. **Offen lassen:** Nach `pflege.verfall_tage` (Standard 42) verfällt der Eintrag.

Grenze: höchstens `pflege.max_aufgaben_pro_runde` Pflegeaufgaben je Wochenrunde (Standard 2), ein Hook zählt nach.

Nebenbefunde, gleich mit behoben:

- Das Entwickler-Gate hat eine Reparatur in `nacharbeit` abgelehnt, weil `tests` und `dateien` leer sind. Die Nacharbeit bei Reparaturen war damit ein toter Pfad.
- Der Reviewer-Diff hat neue Dateien nicht enthalten.

## Folgen

- Eine problematische Aufgabe kostet mehr Reviewer-Läufe als bisher, höchstens vier statt zwei. Die Bedingung „Befunde müssen sinken“ begrenzt das. Eine falsch geschnittene Aufgabe konvergiert nicht und landet wie im Konzept beim Neuschnitt, jetzt über den Supervisor statt automatisch.
- Die Einstufung trägt jetzt Gewicht, weil die Schwelle rechnet. Der Druck auf den Reviewer, herabzustufen, wird durch die Kriterienbindung und die Herkunftsprüfung aufgefangen. Der Auditor kann Stichproben ziehen.
- Der Entwickler behebt in der Nacharbeit nur Befunde, keine Anmerkungen. Die Anmerkungen gehen in die Pflegeliste und nicht in einen Fix, der seinerseits Fehler einbaut.
- Neue Kennzahlen: `fix_befunde_prozent` (Korridor 0–20) und `pflege_verfallen_prozent` (Korridor 0–50).
- Die Git-Trees der Runden-Stände hängen an keinem Commit. `git gc` räumt sie nach der üblichen Frist ab; nach dem Commit der Aufgabe braucht sie niemand mehr.
