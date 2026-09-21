#!/usr/bin/env bash
# PostToolUse for the main session (the Lead): read the exact context size from the transcript and,
# above the configured share of the window, tell the Lead to finish the task, write a handoff and stop.
# Fires once per 10-percent step so it does not nag. Subagents are ignored (they have budgets).
set -euo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
[ -n "$(field '.agent_type')" ] && exit 0
transcript="$(field '.transcript_path')"
[ -f "$transcript" ] || exit 0
proj="$(project_dir)"
window="$($CFG "$proj" budget.context_window 200000)"
threshold="$($CFG "$proj" budget.context_percent 50)"
used="$(tail -c 200000 "$transcript" | jq -s '[.[] | select(.type=="assistant") | .message.usage | (.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0)] | last // 0' 2>/dev/null || echo 0)"
[ "$used" -gt 0 ] || exit 0
percent=$(( used * 100 / window ))
[ "$percent" -ge "$threshold" ] || exit 0
sd="$(state_dir)"
sid="$(field '.session_id')"
step=$(( percent / 10 ))
last="$(cat "$sd/context-$sid.step" 2>/dev/null || echo 0)"
[ "$step" -gt "$last" ] || exit 0
printf '%s\n' "$step" > "$sd/context-$sid.step"
record "context_alarm" "$(jq -n --arg sid "$sid" --argjson used "$used" --argjson percent "$percent" '{session_id:$sid,used:$used,percent:$percent}')"
jq -n --arg msg "keel Kontext-Alarm: Der Kontext dieser Session ist zu $percent % gefüllt (Schwelle $threshold %). Schließe die aktuelle Aufgabe sauber ab, schreibe eine Zwischenübergabe nach .keel/work/handoff/ und beende dich. Ein frischer Lead setzt aus der Übergabe fort." '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$msg}}'
exit 0
