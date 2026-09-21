---
nummer: 0008
titel: PO und Architekt als Rollen mit Abstimmung vor dem ersten Test
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes:
hypothese: Der Mensch schreibt ab jetzt nur noch Backlog-Einträge; „Vorlagen pro Woche“ liegt nach vier Wochen im Korridor 2–5 und „gekippte delegierte ADRs“ unter 10 %
---

# 0008: PO und Architekt als Rollen mit Abstimmung vor dem ersten Test

## Kontext

xXExceptionXx hat am 2026-09-21 die Empfehlung „PO später“ zurückgewiesen: Die Übersetzung von Feature-Wunsch in Problemstellung mit Kriterien ist genau die Arbeit, die er abgeben will. Die Gefahr ist nicht Instabilität, sondern Fehlkalibrierung, und dafür gibt es enge Befugnisse, die wöchentliche Durchsicht delegierter ADRs und die Kennzahl der gekippten ADRs.

## Entscheidung

- **PO** mit vier Anlässen: Problemstellung aus einem Backlog-Element, Abstimmung mit dem Architekten, Klärung von Planer-Fragen, Abnahme gegen den Abnahmenachweis. Entscheidet innerhalb der Befugnisse als delegiertes ADR, sonst Vorlage. Große Wünsche schneidet er in Folge-Vorhaben oder, bei Modellfragen über alle Teile, in ein Epic (ADR 0009).
- **Architekt** mit vier Anlässen: Bewertung in drei Stufen mit Kosten und abgespeckter Variante, Strukturfrage des Planers, Bestandsaufnahme für bestehende Projekte, Wochenrunde gegen Drift.
- **Abstimmung** vor den Abnahmetests: Architekt bewertet, PO entscheidet den Kompromiss, höchstens zwei Runden, dann Vorlage mit beiden Positionen. Der Lead taktet sie als flache, sequenzielle Aufrufe.
- Der Mensch behält: Reihenfolge im Backlog, Maßstab-Dateien, Vorlagen, wöchentliche Durchsicht delegierter ADRs.

## Erprobt

Szenario „Freigabe-Pipeline“ aus drei Sätzen: PO schnitt V5 mit fünf Pflichtkriterien und acht Akzeptanzkriterien und legte zwei Folge-Vorhaben an; Architekt bewertete Stufe 2 mit vier Risiken für spätere Vorhaben; Abstimmung einig in Runde 1 mit zwei delegierten ADRs und einer Vorlage über einen Widerspruch in den Maßstäben. Fünf Aufgaben, ein berechtigter Testeinspruch mit Neuschnitt, Abnahme durch den PO, Integration. Ein Abbruch durch das Nutzungslimit wurde mit einem frischen Lead ohne Sonderbehandlung wieder aufgenommen.

## Folgen

- Der PO ist die einzige Rolle, die Backlog-Elemente in Arbeit nimmt. Der Mensch schreibt Titel, Problem und Warum.
- Die Befugnisse werden bewusst eng gestartet und alle zwei Wochen anhand der gekippten ADRs erweitert.
