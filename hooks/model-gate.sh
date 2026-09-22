#!/usr/bin/env bash
# PreToolUse on Skill: the briefing is a conversation with the Supervisor and must run on the Supervisor's model.
# When /keel:briefing or /keel:start (with a briefing due) is invoked, read the session's model from the
# transcript and deny with instructions if it is not the configured one.
set -uo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
skill="$(field '.tool_input.skill')"
case "$skill" in
  keel:briefing|briefing) needed=1 ;;
  keel:start|start)
    python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$(project_dir)" >/dev/null 2>&1 && exit 0
    needed=1 ;;
  *) exit 0 ;;
esac
proj="$(project_dir)"
required="$($CFG "$proj" supervisor.model claude-fable-5-1)"
transcript="$(field '.transcript_path')"
[ -f "$transcript" ] || exit 0
current="$(tail -c 400000 "$transcript" | jq -r 'select(.type=="assistant") | .message.model // empty' 2>/dev/null | tail -1)"
[ -n "$current" ] || exit 0
[ "$current" = "$required" ] && exit 0
deny "Das Briefing läuft mit dem Supervisor und braucht dessen Modell ($required); diese Session läuft auf $current. Stelle das Modell um (Modellwahl in der App oder /model $required) und rufe $skill erneut auf. Alternativ aus dem Terminal: bash <plugin>/scripts/keel.sh $proj"
