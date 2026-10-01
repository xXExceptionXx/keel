#!/usr/bin/env bash
# PreToolUse for every tool inside a keel role: tool-call budget, test protection, metrics folder protection.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_gate_init keel-only
agent_type="$(field '.agent_type')"
role="$(keel_role "$agent_type")"
[ -n "$role" ] || keel_ok
id="$(field '.agent_id')"
tool="$(field '.tool_name')"
proj="$(project_dir)"
sd="$(state_dir)"

# Metrics folder is off limits for working roles
metrics="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}"
if [ "$role" != "coach" ]; then
  input="$(field '.tool_input | tostring')"
  case "$input" in *"$metrics"*) deny "Der Kennzahlen-Ordner ist für arbeitende Rollen gesperrt" ;; esac
fi

# Developer must not touch the tester's files
ref="$(cat "$sd/agent-$id.ref" 2>/dev/null || true)"
if [ "$role" = "entwickler" ] && [ -n "$ref" ] && [ -f "$proj/.keel/work/tasks/$ref.md" ]; then
  case "$tool" in
    Edit|Write|MultiEdit|NotebookEdit)
      target="$(field '.tool_input.file_path')"
      tests="$(fm_get "$proj/.keel/work/tasks/$ref.md" tests)"
      IFS=',' read -ra arr <<< "$tests"
      for t in ${arr[@]+"${arr[@]}"}; do
        t="${t#"${t%%[![:space:]]*}"}"; t="${t%"${t##*[![:space:]]}"}"
        [ -n "$t" ] && [ "${target#"$proj"/}" = "$t" ] && deny "Der Entwickler darf die Tests des Testers nicht ändern ($t). Bei Widerspruch: Status testeinspruch setzen."
      done
      ;;
  esac
fi

# Time budget
minutes="$(role_limit "$role" minutes 30)"
if [ -f "$sd/agent-$id.start" ]; then
  started="$(cat "$sd/agent-$id.start")"
  is_number "$started" || gate_fail "Startzeit in agent-$id.start unlesbar"
  elapsed=$(( ($(date +%s) - started) / 60 ))
  if [ "$elapsed" -ge "$minutes" ]; then
    target="$(field '.tool_input.file_path')"
    case "$tool:$target" in
      Edit:"$proj"/.keel/work/*|Write:"$proj"/.keel/work/*) ;;
      *)
        record "budget_exhausted" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --argjson minutes "$elapsed" '{role:$role,agent_id:$id,ref:$ref,minutes:$minutes}')" || true
        echo "$elapsed" > "$sd/agent-$id.timeout"
        deny "Zeitbudget erschöpft ($minutes Minuten). Schreibe deinen Stand in die Aufgaben-Datei unter .keel/work/ und beende dich. Keine weiteren Werkzeuge."
        ;;
    esac
  fi
fi

# Tool-call budget
limit="$(role_limit "$role" tool_calls 60)"
calls=0
if [ -f "$sd/agent-$id.calls" ]; then
  calls="$(cat "$sd/agent-$id.calls")"
  is_number "$calls" || gate_fail "Zähler in agent-$id.calls unlesbar"
fi
calls=$((calls + 1))
printf '%s\n' "$calls" > "$sd/agent-$id.calls"
if [ "$calls" -gt "$limit" ]; then
  target="$(field '.tool_input.file_path')"
  case "$tool" in
    Edit|Write)
      case "$target" in
        "$proj"/.keel/work/*) keel_ok ;;
      esac
      ;;
  esac
  record "budget_exhausted" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --argjson calls "$calls" '{role:$role,agent_id:$id,ref:$ref,calls:$calls}')" || true
  deny "Budget erschöpft ($limit Werkzeugaufrufe). Schreibe deinen Stand in die Aufgaben-Datei unter .keel/work/ und beende dich. Keine weiteren Werkzeuge."
fi
keel_ok
