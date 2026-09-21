---
name: kennzahlen
description: Zeigt die Kennzahlen der Lernschleife mit Korridoren, abgeleitet aus Artefakten und Rohdaten. Für den Menschen, nicht für arbeitende Rollen. Aufruf mit /keel:kennzahlen, optional mit Startdatum.
---

Führe aus und gib die Ausgabe unverändert wieder:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/metrics.py" "$PWD" $ARGUMENTS
```

Mit einem Datum als Argument (`YYYY-MM-DD`) wird `--since <Datum>` übergeben. Endet das Skript mit Exit-Code 3, sind Korridore verletzt: sag das in einem Satz und empfiehl `/keel:coach`. Interpretiere die Zahlen nicht selbst, das ist Sache des Coachs.
