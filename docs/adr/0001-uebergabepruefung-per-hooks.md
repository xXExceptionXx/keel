---
nummer: 0001
titel: Übergabeprüfung, Budget und Drei-Zeilen-Grenze als Hooks
status: Accepted
datum: 2026-09-21
entscheider: Ich
hypothese: Rollen halten Übergabeformate ein, ohne dass der Lead nachliest; stop_blocked-Events bleiben unter 20 % der agent_stop-Events
---

# 0001: Übergabeprüfung, Budget und Drei-Zeilen-Grenze als Hooks

## Kontext

Das Konzept verlangt, dass Übergaben feste Artefakte sind und an der Grenze geprüft werden, dass der Lead nur Status liest und dass Aufgaben ein Budget haben. Das war als Eigenkonstruktion markiert. Am 2026-09-21 empirisch geprüft mit Claude Code 2.1.236:

- `PreToolUse` mit Matcher `Agent` liefert `tool_input.prompt` und `tool_input.subagent_type` und kann den Start ablehnen.
- `SubagentStart` und `SubagentStop` liefern `agent_id` und `agent_type` (mit Plugin-Namensraum, z. B. `keel:planer`). `SubagentStop` liefert zusätzlich `last_assistant_message` und `agent_transcript_path`.
- Jeder Werkzeugaufruf innerhalb eines Subagents trägt `agent_id` und `agent_type` in `PreToolUse`.
- Ein `SubagentStop`-Hook blockiert das Beenden mit `{"decision":"block","reason":"…"}`; der Subagent arbeitet mit dem Grund weiter.
- `${CLAUDE_PLUGIN_ROOT}` wird auch im Body von Agent-Definitionen ersetzt.
- Agent-Definitionen können nur Werkzeuge einschränken, keine Pfade.

## Entscheidung

1. **Referenz parken.** Der `Agent`-Hook liest `Aufgabe:` oder `Vorhaben:` aus der ersten Prompt-Zeile, prüft das Eingangsartefakt und schreibt die Referenz nach `state/pending-<rolle>`. `SubagentStart` bindet sie an die `agent_id`. Das funktioniert nur, weil Rollen sequenziell laufen; parallele Starts derselben Rolle wären mehrdeutig.
2. **Ausgangsartefakt bei SubagentStop.** Pro Rolle ein erlaubter Zielstatus und Pflichtfelder. Fehlt etwas, wird das Beenden mit dem konkreten Mangel blockiert. Beim Entwickler laufen zusätzlich Prüftor und Diff-Grenze.
3. **Drei-Zeilen-Grenze** für die Abschlussnachricht ebenfalls bei SubagentStop, weil die Nachricht vollständig im Kontext des Lead landet.
4. **Budget** als Zähler pro `agent_id` in `PreToolUse`. Über der Grenze sind nur noch Schreibzugriffe unter `.keel/work/` erlaubt. Beim Beenden setzt der Hook den Status `budget-erschoepft`, damit die Schleife deterministisch endet.
5. **Kennzahlen-Sperre und Testschutz** im selben `PreToolUse`-Hook, weil Pfad-Regeln nicht pro Agent scopebar sind.
6. **Zustand und Rohdaten** liegen außerhalb des Repos unter `~/.keel-metrics/<projekt>/`.

## Folgen

- Alle Prüfungen sind deterministisch und unabhängig vom Modell.
- Ein Rollen-Prompt muss die erste Zeile exakt einhalten, sonst lehnt der Hook ab. Der Lead-Skill schreibt das vor.
- `claude plugin validate` prüft `hooks/hooks.json` nicht auf gültiges JSON; ein Parse-Fehler schaltet alle Hooks still ab. Die Datei wird deshalb generiert, nicht von Hand geschrieben, und vor jedem Commit mit `jq` geprüft.
- Nicht-interaktive Läufe (`claude -p`) ignorieren `permissions.allow`, bis das Projekt einmal als vertrauenswürdig markiert wurde.
