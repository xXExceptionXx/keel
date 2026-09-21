#!/usr/bin/env bash
# SessionStart: tell the session up front when a Supervisor briefing is due, so the human hears it before working.
set -uo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
proj="$(project_dir)"
[ -f "$proj/.keel/config.yaml" ] || exit 0
out="$(python3 "$PLUGIN_ROOT/scripts/due.py" "$proj" 2>/dev/null)"; rc=$?
[ "$rc" -eq 0 ] && [ "$out" = "nichts fällig" ] && exit 0
if [ "$rc" -ne 0 ]; then
  msg="keel: Fälligkeiten stehen aus, keel-Rollen sind bis dahin gesperrt. Starte /keel:start, es arbeitet sie in Reihenfolge ab. $out"
else
  msg="keel: Hinweise ohne Sperre. $out"
fi
jq -n --arg msg "$msg" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$msg}}'
exit 0
