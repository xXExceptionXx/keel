#!/usr/bin/env bash
# PreToolUse on Skill and UserPromptSubmit (a typed "/keel:<skill>" never passes the Skill tool), three duties:
# 1. /keel:hilfe marks the session as a helper session; agent-gate then denies every role start in it.
# 2. The briefing is a conversation with the Supervisor and must run on the Supervisor's model. When
#    /keel:briefing or /keel:start (with a briefing due) is invoked, read the session's model from the
#    transcript and refuse with instructions if it is not the configured one.
# 3. The start commands start the flow monitor when monitor.autostart is true (System-ADR 0017).
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_gate_init keel-only
event="$(field '.hook_event_name')"
if [ "$event" = "UserPromptSubmit" ]; then
  prompt="$(field '.prompt')"
  skill="$({ printf '%s' "$prompt" | grep -oE '^[[:space:]]*/keel:[a-z]+' || true; } | head -1 | tr -d '[:space:]' | sed 's#^/##')"
  [ -n "$skill" ] || keel_ok
  # a prompt is refused with decision:block, a tool call with a permission deny
  deny() {
    jq -n --arg reason "$1" '{decision:"block",reason:$reason}' || gate_fail "$1"
    record "denied" "$(jq -n --arg hook "skill-gate" --arg reason "$1" '{hook:$hook,role:"",reason:$reason}')" || true
    keel_ok
  }
else
  skill="$(field '.tool_input.skill')"
fi
# The commands that set the system to work also start the flow monitor when monitor.autostart is true.
case "$skill" in
  keel:start|start|keel:vorhaben|vorhaben|keel:epic|epic|keel:tagesstart|tagesstart|keel:briefing|briefing)
    python3 "$PLUGIN_ROOT/scripts/monitor.py" "$(project_dir)" --ensure --if-autostart --quiet --plugin-root "$PLUGIN_ROOT" >/dev/null 2>&1 || true ;;
esac
case "$skill" in
  keel:hilfe|hilfe)
    sid="$(field '.session_id')"
    [ -z "$sid" ] || touch "$(state_dir)/hilfe-$sid"
    keel_ok ;;
  keel:briefing|briefing) needed=1 ;;
  keel:start|start)
    rc=0; br="$(python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$(project_dir)" --json 2>"$ERRF")" || rc=$?
    # exit 1 counts only with a readable answer; a crash before the script's own error handling is exit 1 too
    if [ "$rc" -eq 1 ] && ! printf '%s' "$br" | jq -e '.briefing_noetig == true' >/dev/null 2>&1; then rc=2; fi
    case $rc in
      0) keel_ok ;;
      1) needed=1 ;;
      *) deny "Ob ein Briefing nötig ist, lässt sich nicht prüfen (briefing_needed.py endete mit $rc: $(tail -1 "$ERRF")). /keel:hilfe erklärt den Stand." ;;
    esac ;;
  *) keel_ok ;;
esac
proj="$(project_dir)"
required="$($CFG "$proj" supervisor.model claude-fable-5-1)"
current="$(transcript_model "$(field '.transcript_path')")"
[ -n "$current" ] || keel_ok
[ "$current" != "$required" ] || keel_ok
deny "Das Briefing läuft mit dem Supervisor und braucht dessen Modell ($required); diese Session läuft auf $current. Stelle das Modell um (Modellwahl in der App oder /model $required) und rufe $skill erneut auf. Alternativ aus dem Terminal: bash <plugin>/scripts/keel.sh $proj. Unklar, was los ist: /keel:hilfe erklärt den Stand."
