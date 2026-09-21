# Architekturdokument

<!-- Pflegt: Architekt. Liest: Planer, Auditor. Dauerhaft. -->

## Komponenten und Grenzen

_C4-Kontext und Container. Welche Teile gibt es, was darf was importieren?_

Orte für Tests, die der Tester und der Lead brauchen: Aufgabentests, Abnahmetests (laufen getrennt, bis das Vorhaben abgenommen ist) und Regressionstests (Abnahmetests abgenommener Vorhaben, laufen im Prüftor mit).

## Muster und Referenzbeispiele

| Muster | Referenzbeispiel im Code | Prüfregel |
| --- | --- | --- |
| _z. B. Feature-Schnitt_ | _`src/features/beispiel/`_ | _Import-Grenzen im Linter_ |

## Das Warum hinter den Regeln

_Nur Prosa für das, was sich nicht prüfen lässt._
