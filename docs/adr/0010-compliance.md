---
nummer: 0010
titel: Compliance als deterministischer Scan mit Ermessensrolle dahinter
status: Accepted
datum: 2026-09-21
entscheider: Ich
supersedes:
hypothese: Kein Secret und keine ungeplante Abhängigkeit erreicht mehr einen Review; die Compliance-Rolle läuft nur bei Befunden der Klasse „pruefen“ und in weniger als einem Fünftel der Aufgaben
---

# 0010: Compliance als deterministischer Scan mit Ermessensrolle dahinter

## Kontext

Das Konzept sieht Compliance als Hook für Deterministisches und als Agent nur für Ermessensfragen vor, mit der Warnung: „nur bei Ermessensfragen“ heißt in der Praxis nie, wenn niemand entscheidet, dass eine vorliegt. Vor dem Einsatz in einem Projekt, das personenbezogene Daten verarbeitet, muss der Auslöser deterministisch sein.

## Entscheidung

- `scripts/compliance_scan.py` läuft beim Beenden jedes Entwicklers nach dem Prüftor über den Diff der Aufgabe: Secrets und private Schlüssel (blockiert das Beenden), neue Abhängigkeiten aus den Manifesten per Schlüsselvergleich (Klasse `vorlage`, der Mensch entscheidet laut Befugnissen), Muster personenbezogener Daten in Typen, Schemas und Migrationen, neue externe Aufrufe und Logging solcher Felder (Klasse `pruefen`). Projektmuster über `compliance.pii_patterns`.
- Der Scan schreibt `.keel/work/compliance/<ID>.scan.md` und setzt `compliance` in der Aufgabe. Der Lead reagiert: `vorlage` wird Vorlage, `pruefen` ruft die Rolle `keel:compliance`.
- Die Rolle prüft nach DSGVO gegen Zweck, Rechtsgrundlage, Empfänger, Löschfristen und ein optionales `.keel/datenschutz.md`. Ergebnis `frei`, `auflagen` (Nacharbeit durch den Entwickler) oder `vorlage` (Frage an den Menschen). Sie ändert keinen Code und entscheidet nicht über Produkt oder Architektur.

## Folgen

- Ein Projekt mit personenbezogenen Daten sollte `.keel/datenschutz.md` pflegen: Verarbeitungen, Rechtsgrundlagen, Auftragsverarbeiter, Löschfristen. Ohne die Datei wird die Rolle häufiger `vorlage` melden, was richtig ist.
- Lizenzprüfung neuer Abhängigkeiten ist Teil der Vorlage, nicht des Scans.
