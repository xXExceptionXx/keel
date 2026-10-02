#!/usr/bin/env bash
# Stop of the main session: when a briefing ran in it, its protocol must leave no open point behind
# (System-ADR 0021). Checked only once a protocol was written since the briefing started; before that the
# briefing is still a conversation. A finding blocks the stop with the reasons, at most three times; then the
# hook lets go and records briefing_protokoll_offen. An observer: an internal failure never traps the session.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_observer_init
proj="$(project_dir)"
[ -d "$proj/.keel" ] || keel_ok
sid="$(field '.session_id')"
[ -n "$sid" ] || keel_ok
keel_paths || keel_ok
marker="$KEEL_PATH_STATE/briefing-$sid.json"
[ -f "$marker" ] || keel_ok
rc=0; out="$(python3 "$PLUGIN_ROOT/scripts/wiedervorlage.py" protokoll "$proj" --stand "$marker" 2>"$ERRF")" || rc=$?
[ "$rc" -le 1 ] || { hook_error "Briefing-Protokoll nicht prüfbar: $(tail -1 "$ERRF")"; rm -f "$marker"; keel_ok; }
result="$(printf '%s' "$out" | jq -r '.ergebnis')"
case "$result" in
  offen) keel_ok ;;
  ok)
    rm -f "$marker"
    record "briefing_geprueft" "$(printf '%s' "$out" | jq -c '{protokoll:.protokoll}')" || true
    keel_ok ;;
  aufgegeben)
    rm -f "$marker"
    record "briefing_protokoll_offen" "$(printf '%s' "$out" | jq -c '{protokoll:.protokoll,gruende:.gruende}')" || true
    keel_ok ;;
  fehler)
    reason="Das Briefing-Protokoll lässt offene Punkte zurück. Jeder offene Punkt wird eine Wiedervorlage (wiedervorlage.py neu) und steht unter '## Zurückgestellt'; danach das Protokoll ergänzen und committen: $(printf '%s' "$out" | jq -r '.gruende | join("; ")')"
    KEEL_DONE=1
    jq -n --arg reason "$reason" '{decision:"block",reason:$reason}'
    record "stop_blocked" "$(jq -n --arg reason "$reason" '{role:"supervisor",agent_id:"",ref:"briefing",reason:$reason}')" || true
    exit 0 ;;
  *) hook_error "unerwartete Antwort von wiedervorlage.py protokoll: $out"; rm -f "$marker"; keel_ok ;;
esac
