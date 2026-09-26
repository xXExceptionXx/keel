#!/usr/bin/env bash
# keel launcher for the terminal: opens an interactive Claude Code session with the right model and /keel:start.
# Usage: keel.sh [project-dir]   (default: current directory)
# Picks the Supervisor's model when a briefing is due, otherwise the session default.
set -uo pipefail
project="$(cd "${1:-.}" && pwd)"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project" || exit 2
python3 "$PLUGIN_ROOT/scripts/monitor.py" "$project" --ensure --if-autostart --plugin-root "$PLUGIN_ROOT" || true
if python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$project" >/dev/null 2>&1; then
  exec claude "/keel:start"
else
  model="$(python3 "$PLUGIN_ROOT/scripts/config.py" "$project" supervisor.model claude-fable-5-1)"
  echo "Briefing fällig: Session läuft auf $model."
  exec claude --model "$model" "/keel:start"
fi
