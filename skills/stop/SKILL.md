---
name: stop
description: Der eine Ausstieg aus keel. Tagesabschluss mit Übergabenotiz und Tag, danach der Audit, dann ein Satz, was morgen ansteht. Aufruf mit /keel:stop am Ende des Arbeitstags.
---

Du bist der Lead im keel-System und schließt den Tag ab.

1. Führe den Ablauf aus der Skill `keel:tagesabschluss` aus. Endet er an einer halbfertigen Aufgabe, sag das und beende; der Mensch entscheidet, ob er die Aufgabe zu Ende laufen lässt (`/keel:start`) oder zurücksetzt.
2. Führe den Ablauf aus der Skill `keel:audit` aus.
3. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/due.py" "$PWD"` und gib die Ausgabe wieder.
4. Schließe mit einem Satz: was morgen bei `/keel:start` als Erstes passiert (Briefing, Coach, oder direkt das nächste Vorhaben).
