---
nummer: 0003
titel: Branch pro Vorhaben und pro Reparatur, Merge nach Abnahme durch den Lead
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes: 0002
hypothese: Der Hauptzweig ist zu jedem Zeitpunkt abgenommener Stand; Merge-Konflikte bleiben bei sequenzieller Arbeit die Ausnahme
---

# 0003: Branch pro Vorhaben und pro Reparatur

## Kontext

ADR 0002 hatte Branches zugunsten eines einfacheren Tagesrhythmus gestrichen. xXExceptionXx hat das am 2026-09-21 zurückgewiesen: Ein Feature oder ein Bug wird auf einem Branch gelöst, das ist der Maßstab, nicht die Bequemlichkeit des Audits.

## Entscheidung

- `/keel:vorhaben <name>` arbeitet auf `vorhaben/<name>`, abgezweigt von `main` nach grünem Startcheck. Ein Commit pro Aufgabe mit Trailer `Keel-Task`. Der Branch wird gepusht und bleibt bis zur Abnahme.
- Abnahme ist ein Statuswechsel durch den PO (`abgenommen`). Danach integriert der Lead: Merge `--no-ff` nach `main`, Abnahmetests in die Regressionssuite, Status `integriert`, Branch löschen.
- Reparaturen laufen auf `reparatur/<ID>` und werden nach bestandenem Review sofort vom Lead gemergt; sie brauchen keine PO-Abnahme.
- Tagesabschluss und Audit laufen auf dem aktiven Branch. Das Tages-Tag zeigt dorthin. `/keel:tagesstart` beginnt auf `main`.

## Folgen

- `main` enthält nur abgenommene Vorhaben und gemergte Reparaturen. Der Startcheck auf `main` ist damit der Nachweis, dass der abgenommene Stand läuft.
- Abnahmetests laufen nach der Integration im Prüftor jeder Aufgabe mit. Das schließt das Regressionsloch, das bei der Abnahme von V1 und V2 aufgefallen ist.
- Deny-Regeln bleiben: `git branch -D` ist gesperrt, gemergte Branches werden mit `-d` gelöscht.
