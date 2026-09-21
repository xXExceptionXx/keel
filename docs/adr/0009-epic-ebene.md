---
nummer: 0009
titel: Epic-Ebene mit Leitentscheidungen nach Reichweite, Retrospektive und Kurskorrektur
status: Accepted
datum: 2026-09-21
supersedes:
entscheider: Ich
hypothese: In Epics mit drei oder mehr Vorhaben wird keine Leitentscheidung nach dem ersten Vorhaben still umgestoßen; jede Kurskorrektur erscheint als Vorlage, bevor das nächste Vorhaben geplant wird
---

# 0009: Epic-Ebene

## Kontext

Die Erfahrung von xXExceptionXx mit einer Moderations-Pipeline in einem anderen Projekt: Das Modell (Status an der Entität) musste mitten im Vorhaben auf Elementebene umgeschwenkt werden, weil die Frage erst mit den späteren Paketen sichtbar wurde. Eine Recherche zu Anthropic, Cursor, Spec Kit, Kiro und BMAD zeigte: Fast alle Systeme halten ein Dach-Artefakt über den Arbeitseinheiten und sichern seine Frische über Flughöhe, Rückschreibung und Retrospektive.

## Entscheidung

- **Epic-Datei** `.keel/work/epics/<name>.md`: Zielbild des Themas, Nicht-Ziele, Vorhaben-Liste mit Nutzen, Abhängigkeit und Status, Leitfragen, Done-Condition, Bedenken-Log, Retrospektiven.
- **Epic-Bewertung des Architekten nach Reichweite:** Welche Entscheidung im ersten Vorhaben müsste ein späteres wieder umstoßen. Je Entscheidung Optionen, Kosten jetzt, Kosten der Umkehr, ob das erste Vorhaben sie erzwingt.
- **Leitentscheidungen als ADR vor dem ersten Vorhaben.** Innerhalb der Befugnisse entscheidet der PO, sonst eine Vorlage je Entscheidung an den Menschen; Datenmodell und Architekturgrenzen sind der Regelfall.
- **Tracer Bullet:** Das erste Vorhaben ist der dünnste Ende-zu-Ende-Pfad, der Architekt prüft das.
- **Retrospektive** nach jeder Integration: Hält der Code die Leitentscheidungen, war eine falsch. Kurskorrektur wird eine Vorlage mit drei Optionen, bevor das nächste Vorhaben geplant wird.
- **Bedenken-Log:** Risiken aus Bewertungen wandern ins Epic, damit spätere Vorhaben sie sehen.
- Skill `/keel:epic`; `/keel:vorhaben` kennt die Epic-Zugehörigkeit; der Reviewer bleibt pro Aufgabe.

## Folgen

- Der Konzeptwechsel wird nicht verhindert, sondern ein benanntes Ereignis mit Entscheidung.
- Grenze: Innerhalb eines Vorhabens prüft nur der Reviewer gegen die Akzeptanzkriterien; Modellbrüche mitten in einem Vorhaben werden am Ende des Vorhabens sichtbar, nicht in Aufgabe zwei. Die Grenze von sechs Aufgaben hält das klein.
- Ein Epic wird fertig, wenn seine Done-Condition grün ist, nicht wenn die Liste leer ist.
