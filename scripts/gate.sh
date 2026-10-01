#!/usr/bin/env bash
# keel gate (Prüftor): run the project's test command, keep the full output in the log folder,
# print one summary line. Exit 0 when green, 124 when the time limit test.timeout (seconds) was hit.
# The limit must stay below the SubagentStop hook timeout in hooks/hooks.json: a hook that times out
# lets the stop through (System-ADR 0019).
# Usage: gate.sh <project-dir> <label>
set -uo pipefail
proj="$1"; label="${2:-gate}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cmd="$(python3 "$PLUGIN_ROOT/scripts/config.py" "$proj" test.command "npm test --silent")"
limit="$(python3 "$PLUGIN_ROOT/scripts/config.py" "$proj" test.timeout 480)"
case "$limit" in ''|*[!0-9]*) limit=480 ;; esac
# Cap below the SubagentStop hook timeout (600 s) with room for the rest of the hook.
note=""
if [ "$limit" -gt 540 ]; then note=" (test.timeout $limit auf 540 s begrenzt, Hook-Timeout 600 s)"; limit=540; fi
logdir="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}/$(basename "$proj")/logs"
mkdir -p "$logdir"
log="$logdir/$label-$(date -u +%Y%m%dT%H%M%SZ).log"
( cd "$proj" && python3 "$PLUGIN_ROOT/scripts/timeout.py" "$limit" -- bash -c "$cmd" ) > "$log" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
  echo "gate: grün ($cmd), Log: $log$note"
elif [ $rc -eq 124 ]; then
  echo "gate: rot, abgebrochen nach $limit s ($cmd), Log: $log. Grenze: test.timeout in .keel/config.yaml.$note"
  tail -20 "$log"
else
  echo "gate: rot (exit $rc, $cmd), Log: $log"
  tail -20 "$log"
fi
exit $rc
