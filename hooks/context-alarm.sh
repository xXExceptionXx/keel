#!/usr/bin/env bash
# PostToolUse for the main session (the Lead): read the exact context size from the transcript and,
# above the configured share of the window, tell the Lead to finish the task, write a handoff and stop.
# Fires once per 10-percent step so it does not nag. Subagents are ignored (they have budgets).
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_observer_init
agent_type="$(field '.agent_type')"
[ -z "$agent_type" ] || keel_ok
transcript="$(field '.transcript_path')"
[ -f "$transcript" ] || keel_ok
proj="$(project_dir)"
window="$($CFG "$proj" budget.context_window 200000)"
threshold="$($CFG "$proj" budget.context_percent 50)"
# Line by line: the tail starts in the middle of a line, which "jq -s" would reject as a whole.
used="$(tail -c 400000 "$transcript" | jq -nR '[inputs | fromjson? | select(.type=="assistant") | .message.usage | select(. != null) | (.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0)] | last // 0' 2>/dev/null || echo 0)"
is_number "$used" || used=0
[ "$used" -gt 0 ] || keel_ok
percent=$(( used * 100 / window ))
[ "$percent" -ge "$threshold" ] || keel_ok
sd="$(state_dir)"
sid="$(field '.session_id')"
step=$(( percent / 10 ))
last="$(cat "$sd/context-$sid.step" 2>/dev/null || echo 0)"
is_number "$last" || last=0
[ "$step" -gt "$last" ] || keel_ok
# Say it first: a failing record must not swallow the alarm while the step already counts as reported.
jq -n --arg msg "keel Kontext-Alarm: Der Kontext dieser Session ist zu $percent % gefüllt (Schwelle $threshold %). Schließe die aktuelle Aufgabe sauber ab, schreibe eine Zwischenübergabe nach .keel/work/handoff/ und beende dich. Ein frischer Lead setzt aus der Übergabe fort." '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$msg}}'
printf '%s\n' "$step" > "$sd/context-$sid.step" || true
record "context_alarm" "$(jq -n --arg sid "$sid" --argjson used "$used" --argjson percent "$percent" '{session_id:$sid,used:$used,percent:$percent}')" || true
keel_ok
