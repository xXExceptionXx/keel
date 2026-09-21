---
nummer: 0007
titel: Belege der Übergabenotiz werden mechanisch geprüft, bevor der Tag gesetzt wird
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes:
hypothese: Bis 2026-10-21 taucht in keinem Prüfbericht ein Befund der Klasse „Verweis existiert nicht“ auf; „Audit-Abweichungen pro Bericht“ sinkt auf höchstens 4, „Blockierte Übergaben“ bleibt unter 20 %
---

# 0007: Belege der Übergabenotiz werden mechanisch geprüft

## Kontext

Vorlage des Coachs vom 2026-09-21: Zwei Prüfbefunde betrafen Verweise in der Übergabenotiz. Bei der Umsetzung zeigte sich, dass einer davon selbst falsch war: Der Logname existierte im Kennzahlen-Ordner, den der Auditor nicht sehen darf. Ein Skript, das beide Log-Orte kennt, hätte den Fehlbefund vermieden.

## Entscheidung

Option 1 mit Option 2 als Nebeneffekt, entschieden von xXExceptionXx. `scripts/check_references.py` prüft Lognamen (Projekt- und Kennzahlen-Logs), Commit-IDs (`git cat-file -e`) und Dateipfade eines Artefakts. Der Tagesabschluss führt es vor dem Tag aus und setzt keinen Tag mit defekten Verweisen; Lognamen werden aus der Ausgabe des Test-Skills übernommen, nie getippt. Der Auditor führt dasselbe Skript für den Abgleich „Übergabenotiz vs. Code“ aus und konzentriert seinen eigenen Blick auf die Wahrheit der Angaben.

## Folgen

- Existenz wird mechanisch geprüft, Wahrheit bleibt Sache des Auditors.
- Bloße Dateinamen in Backticks gelten als vorhanden, wenn irgendwo im Projekt eine Datei dieses Namens liegt; das vermeidet Fehlalarme bei Erwähnungen wie `settings.json`.
