---
name: backlog
description: Bedient das Backlog über die Schnittstelle, unabhängig vom Anbieter (Markdown-Datei oder GitHub Issues). Aufruf mit /keel:backlog <befehl>, etwa next, list, show BL-3, propose <datei>, status BL-3 bereit.
---

Das Backlog wird nur über dieses Skript bedient, nie direkt über die Datei oder die GitHub-Oberfläche aus einer Rolle heraus:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog.py" $ARGUMENTS
```

Befehle: `next` (höchstpriorisiertes Element mit Status bereit), `show <id>`, `list [--status <status>]`, `propose <datei>` (Markdown mit Frontmatter titel, problem, warum, herkunft), `status <id> <status>`, `link <id> <plan-pfad>`. Kanonische Zustände: vorgeschlagen, bereit, in-arbeit, erledigt, verworfen. Der Anbieter steht in `.keel/config.yaml` unter `backlog.provider`; die Reihenfolge (Priorität) pflegt der Mensch im Werkzeug selbst.

Gib das JSON-Ergebnis in ein bis drei Zeilen zusammengefasst wieder. Beim Start eines Vorhabens aus einem Element: `status <id> in-arbeit` und `link <id> .keel/work/plans/<name>.md`; die Problemstellung wird in der Plan-Datei eingefroren, damit das System danach ohne das Werkzeug auskommt.
