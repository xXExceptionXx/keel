---
name: init
description: Richtet keel in einem Projekt ein. Legt .keel/ mit Vorlagen an, verlinkt .claude/skills, ergänzt Deny-Regeln in .claude/settings.json und den Import in CLAUDE.md. Aufruf mit /keel:init, idempotent.
---

Richte keel im aktuellen Projekt ein. Führe dafür genau diesen Befehl aus:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/init.sh" $ARGUMENTS
```

Das Skript ist idempotent und überschreibt keine bestehenden Dateien. Gib dem Nutzer danach die Ausgabe des Skripts in Kurzform wieder: was angelegt wurde, was schon vorhanden war, und welche Dateien er als Nächstes ausfüllen sollte. Lies keine der Vorlagen ein und fülle nichts selbst aus; das Zielbild, die Qualitätsmerkmale und die Befugnisse schreibt der Mensch.

Schlägt das Skript fehl, gib die Fehlermeldung unverändert wieder und schlage keine Alternative vor, die die Deny-Regeln umgeht.
