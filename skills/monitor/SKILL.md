---
name: monitor
description: Startet den Ablauf-Monitor, eine lokale Webseite mit aktiver Rolle, Fälligkeiten, Vorhaben samt Zeitleiste, Vorlagen, Ereignisstrom und allen Übergaben unter .keel/ als lesbare Dokumente. Beobachtet nur. Aufruf mit /keel:monitor, optional mit einem Port oder „stop“.
---

Du startest oder beendest den keel-Monitor für dieses Projekt und sagst dem Menschen, wo er ihn findet. Sonst tust du nichts. Argument, falls angegeben: `$ARGUMENTS` (ein Port oder `stop`).

## Ablauf

1. **Starten** (ohne Argument oder mit Port):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/monitor.py" "$PWD" --ensure --plugin-root "${CLAUDE_PLUGIN_ROOT}" [--port <port>]
   ```

   Ohne Port gilt `monitor.port` aus `.keel/config.yaml`, sonst 8765. Der Server läuft losgelöst weiter, auch nach dem Ende dieser Session; läuft er schon, wird kein zweiter gestartet. Gib die ausgegebene Adresse in einem Satz weiter. Meldet er einen belegten Port, nenne die Meldung und schlage `monitor.port` oder `/keel:monitor <port>` vor.

2. **Beenden** (`stop`): `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/monitor.py" "$PWD" --stop` und die Ausgabe in einem Satz.

3. **Immer mitstarten:** Wer den Monitor bei jeder Arbeit sehen will, setzt `monitor.autostart: true` in `.keel/config.yaml`. Dann starten ihn `/keel:start`, `vorhaben`, `epic`, `tagesstart`, `briefing`, `keel.sh` und `keel-run.sh` mit. Nenne das, wenn der Mensch fragt, wie er ihn dauerhaft bekommt; die Datei änderst du nicht selbst.

## Regeln

- **Der Monitor beobachtet nur** (System-ADR 0017). Er liest Zustand, Ereignisse und Dateien und schreibt nichts unter `.keel/`. Du erweiterst ihn hier nicht um Schreibwege.
- Du startest keine Rolle und keinen Ablauf. Soll gearbeitet werden: `/keel:start`, gern in einer anderen Session, während der Monitor zusieht.
- Fragen zum Stand beantwortet `/keel:hilfe`; die Seite zeigt ihn, sie erklärt ihn nicht.
