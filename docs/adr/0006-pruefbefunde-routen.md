---
nummer: 0006
titel: Prüfbefunde werden am Tagesstart mechanisch geroutet
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes:
hypothese: „Audit-Abweichungen pro Bericht“ sinkt von 8 auf höchstens 3 bis 2026-10-21; ab dem zweiten Prüfbericht trägt jeder Befund eine Backlog- oder Vorlagen-ID; offene Befunde aus dem Vorbericht tauchen in keinem Folgebericht erneut als Abweichung auf
---

# 0006: Prüfbefunde werden am Tagesstart mechanisch geroutet

## Kontext

Vorlage des Coachs vom 2026-09-21: Von acht Befunden des ersten Prüfberichts sind drei versandet, weil der Vermerk „wird Aufgabe | wird Vorlage“ der letzte Ort war, an dem ein Befund existierte. Das Konzept weist das Routen dem PO zu, der Ablauf kannte den Schritt nicht.

## Entscheidung

Option 1 der Vorlage, entschieden von xXExceptionXx. `/keel:tagesstart` ruft `scripts/route_findings.py` auf: Jeder Befund des jüngsten Prüfberichts ohne ID wird zu einem Backlog-Element mit Herkunft Audit oder zu einer Vorlage, die ID wird in den Bericht geschrieben. Der Lead urteilt nicht, der Vermerk des Auditors entscheidet das Ziel; der Mensch entscheidet im Backlog, ob aus „vorgeschlagen“ ein „bereit“ wird. Der Auditor führt geroutete Befunde nicht erneut als Abweichung, sondern unter „Offen aus früheren Berichten“.

## Folgen

- Der Auditor bleibt schreibfrei, der Tagesstart kostet keinen zusätzlichen Rollenlauf, das Routen ist ein Skript.
- Die Inbox zeigt Backlog-Vorschläge, damit der Mensch die gerouteten Befunde sieht.
- Die Kennzahl „Audit-Abweichungen pro Bericht“ misst ab jetzt neue Befunde, nicht Altlast.
