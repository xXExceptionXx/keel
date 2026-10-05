---
nummer: 0026
titel: Im Briefing erst vorstellen, dann fragen; Dateien des Menschen nur nach ausdrücklichem Übernehmen
status: Accepted
datum: 2026-10-05
entscheider: Ich
supersedes:
hypothese: Im nächsten Briefing hat jede Frage ihren Gegenstand vorher im Wortlaut gezeigt, keine Frage bündelt zwei Änderungen, und jede Änderung an einer Datei des Menschen bietet „so übernehmen“ an
---

# 0026: Im Briefing erst vorstellen, dann fragen; Dateien des Menschen nur nach ausdrücklichem Übernehmen

## Kontext

Im ersten Briefing des neuen Beispielprojekts fragte der Supervisor am Ende in einer einzigen Frage nach zwei Änderungen an Dateien des Menschen (Qualitätsmerkmal Rang 1, `docs/adr/TEMPLATE.md`), ohne heutigen und vorgeschlagenen Wortlaut zu zeigen. Er bot nur „Wiedervorlage, du änderst es selbst“ oder „ablehnen“ an: Die Regel „Maßstab-Dateien ändert nur der Mensch“ hatte er so gelesen, dass er sie auch mit dem Ja des Menschen nicht ändern darf. Der Mensch konnte weder beurteilen noch übernehmen.

## Entscheidung

- Die Briefing-Skill bekommt einen Abschnitt „Wie du vorlegst“: Jeder Punkt wird vor der Frage ausgeschrieben, bei Textänderungen mit heutigem und vorgeschlagenem Wortlaut, mit Folge ohne Änderung und Empfehlung. Eine Entscheidung je Frage.
- Für Dateien des Menschen (Zielbild, Qualitätsmerkmale, Befugnisse, Roadmap, `.keel/config.yaml` einschließlich `freigaben.befehle`, ADRs aus `adr.weitere_ordner`, Projekt-Doku außerhalb von `.keel/`) bietet der Supervisor immer vier Optionen: so übernehmen, anders formulieren, Wiedervorlage, ablehnen. Bei „so übernehmen“ ändert er die Datei in der Briefing-Session mit genau dem gezeigten Wortlaut; das Protokoll nennt sie unter `## Geändert im Auftrag`.
- Tagsüber bleibt es dabei: Keine Rolle ändert diese Dateien; der Supervisor schreibt nötige Anpassungen als Empfehlung in seine Entscheidung.

## Verworfen

- **Der Mensch ändert seine Dateien immer selbst.** Das macht aus jeder kleinen Nachführung eine Wiedervorlage und eine Woche Verzug, obwohl er im Briefing dabeisitzt und zustimmen kann.

## Folgen

- Das Briefing wird etwas länger, Fragen ohne Gegenstand fallen weg.
- Der Hook für ADR-Ordner des Projekts (System-ADR 0024) prüft nur Rollenläufe; Änderungen im Briefing stehen im Protokoll und im Commit.
