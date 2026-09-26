---
name: monitor
description: Startet den Ablauf-Monitor, eine lokale Webseite mit aktiver Rolle, Fälligkeiten, Vorhaben, Vorlagen, Ereignisstrom und allen Übergaben unter .keel/ als lesbare Dokumente. Beobachtet nur. Aufruf mit /keel:monitor, optional mit einem Port.
---

Du startest den keel-Monitor für dieses Projekt und sagst dem Menschen, wo er ihn findet. Sonst tust du nichts. Port, falls angegeben: `$ARGUMENTS` (Standard 8765).

## Ablauf

1. Starte den Server als Hintergrundprozess (Bash mit `run_in_background: true`), damit die Session frei bleibt:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/monitor.py" "$PWD" --plugin-root "${CLAUDE_PLUGIN_ROOT}" --port <port>
   ```

2. Lies die erste Zeile der Ausgabe. Steht dort die Adresse, gib sie in einem Satz weiter: „Monitor läuft auf http://127.0.0.1:<port>/ – er lebt so lange wie diese Session.“ Meldet er einen belegten Port, läuft vermutlich schon ein Monitor; nenne die Adresse und biete einen anderen Port an.

3. Ohne diese Session, aus dem Terminal: `python3 <plugin>/scripts/monitor.py <projekt>`. Nenne das, wenn der Mensch den Monitor dauerhaft neben der Arbeit laufen lassen will.

## Regeln

- **Der Monitor beobachtet nur** (System-ADR 0017). Er liest Zustand, Ereignisse und Dateien und schreibt nichts. Du erweiterst ihn hier nicht um Schreibwege.
- Du startest keine Rolle und keinen Ablauf. Soll gearbeitet werden: `/keel:start`, gern in einer anderen Session, während der Monitor zusieht.
- Fragen zum Stand beantwortet `/keel:hilfe`; die Seite zeigt ihn, sie erklärt ihn nicht.
