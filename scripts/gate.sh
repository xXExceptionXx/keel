#!/usr/bin/env bash
# keel gate (Prüftor): run the project's test command, keep the full output in the log folder,
# print one summary line. Exit 0 when green.
# Usage: gate.sh <project-dir> <label>
set -uo pipefail
proj="$1"; label="${2:-gate}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cmd="$(python3 "$PLUGIN_ROOT/scripts/config.py" "$proj" test.command "npm test --silent")"
logdir="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}/$(basename "$proj")/logs"
mkdir -p "$logdir"
log="$logdir/$label-$(date -u +%Y%m%dT%H%M%SZ).log"
( cd "$proj" && bash -c "$cmd" ) > "$log" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
  echo "gate: grün ($cmd), Log: $log"
else
  echo "gate: rot (exit $rc, $cmd), Log: $log"
  tail -20 "$log"
fi
exit $rc
