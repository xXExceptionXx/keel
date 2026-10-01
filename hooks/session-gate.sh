#!/usr/bin/env bash
# SessionStart: tell the session up front when a Supervisor briefing is due, so the human hears it before working.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_observer_init
proj="$(project_dir)"
[ -f "$proj/.keel/config.yaml" ] || keel_ok
rc=0; out="$(python3 "$PLUGIN_ROOT/scripts/due.py" "$proj" 2>/dev/null)" || rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "nichts fällig" ]; then keel_ok; fi
if [ "$rc" -ne 0 ]; then
  msg="keel: Fälligkeiten stehen aus, keel-Rollen sind bis dahin gesperrt. Starte /keel:start, es arbeitet sie in Reihenfolge ab. $out"
  case "$out" in
    *briefing*) msg="$msg Das Briefing braucht das Modell des Supervisors ($($CFG "$proj" supervisor.model claude-fable-5-1)); stelle es vor /keel:start um." ;;
  esac
else
  msg="keel: Hinweise ohne Sperre. $out"
fi
msg="$msg Für eine Erklärung des Stands: /keel:hilfe."
jq -n --arg msg "$msg" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$msg}}'
keel_ok
