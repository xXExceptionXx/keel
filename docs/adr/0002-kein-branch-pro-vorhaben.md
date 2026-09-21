---
nummer: 0002
titel: Kein Branch pro Vorhaben, solange ein Lead sequenziell arbeitet
status: Superseded by 0003
datum: 2026-09-21
entscheider: Ich
hypothese: Nachvollziehbarkeit pro Vorhaben bleibt über Aufgaben-IDs in Commits erhalten; kein Bedarf an Branches, bis zwei Leads parallel arbeiten
---

# 0002: Kein Branch pro Vorhaben, solange ein Lead sequenziell arbeitet

## Kontext

Das Konzept sieht einen Branch pro Vorhaben vor, gemergt nach der Abnahme. Im ersten Lauf hat sich gezeigt, dass Tagesabschluss, Tages-Tag und Audit-Diff auf einem einzigen Zweig deutlich einfacher sind: Der Auditor prüft „seit dem letzten Tag“, der Startcheck prüft „den Hauptzweig“, und beides ist eindeutig, wenn es nur einen Zweig gibt.

## Entscheidung

Der Lead committet Aufgaben direkt auf `main`, ein Commit pro Aufgabe mit der Aufgaben-ID im Betreff und dem Trailer `Keel-Task: <ID>`. Ein Vorhaben lässt sich über `git log --grep 'Keel-Task: V1-'` vollständig nachvollziehen und mit `git revert` pro Aufgabe zurücknehmen.

Branches kommen, wenn zwei Leads parallel arbeiten oder ein Projekt einen geschützten Hauptzweig mit Pull Requests verlangt. Dann wird diese Entscheidung durch eine neue ersetzt.

## Folgen

- Ein rotes Prüftor auf `main` blockiert alles Weitere, deshalb läuft die Reparaturaufgabe mit Vorrang.
- Die Abnahme durch den PO ist kein Merge, sondern ein Statuswechsel im Plan.
- Der Abschnitt „Integration und Zustand“ im Konzept wird entsprechend angepasst.
