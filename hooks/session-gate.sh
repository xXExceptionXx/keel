#!/usr/bin/env bash
# SessionStart: tell the session up front when a Supervisor briefing is due, so the human hears it before working.
set -uo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
proj="$(project_dir)"
[ -f "$proj/.keel/config.yaml" ] || exit 0
out="$(python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$proj" 2>/dev/null)" && exit 0
jq -n --arg msg "keel: Ein Briefing mit dem Supervisor ist nötig, bevor der Lead arbeitet. Starte /keel:briefing; keel-Rollen außer dem Supervisor sind bis dahin gesperrt. $out" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$msg}}'
exit 0
