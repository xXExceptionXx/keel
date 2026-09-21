#!/usr/bin/env bash
# PreToolUse on Agent: a keel role may only start when its input handoff exists and has the right status.
# Also parks the task or plan reference so SubagentStart can bind it to the agent id.
set -euo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

type="$(field '.tool_input.subagent_type')"
role="$(keel_role "$type")"
[ -z "$role" ] && exit 0

prompt="$(field '.tool_input.prompt')"
task="$(prompt_field "$prompt" "Aufgabe")"
plan="$(prompt_field "$prompt" "Vorhaben")"
proj="$(project_dir)"
tasks="$proj/.keel/work/tasks"
plans="$proj/.keel/work/plans"

case "$role" in
  probe) ;;
  planer)
    if [ -n "$task" ]; then
      $FM validate "$tasks/$task.md" --type aufgabe --status neuschnitt 2>/tmp/keel-gate-err \
        || deny "Planer (Neuschnitt) darf nicht starten: $(cat /tmp/keel-gate-err)"
    else
      [ -n "$plan" ] || deny "Planer braucht die Zeile 'Vorhaben: <name>' oder 'Aufgabe: <ID>' im Prompt"
      $FM validate "$plans/$plan.md" --type plan --status abnahmetests-bereit 2>/tmp/keel-gate-err \
        || deny "Planer darf nicht starten: $(cat /tmp/keel-gate-err). Erst der Tester mit Abnahmetests."
    fi
    ;;
  auditor|coach)
    datum="$(prompt_field "$prompt" "Datum")"
    [ -n "$datum" ] || deny "$role braucht die Zeile 'Datum: YYYY-MM-DD' im Prompt"
    task="$datum"
    ;;
  tester)
    if [ -n "$task" ]; then
      $FM validate "$tasks/$task.md" --type aufgabe --status geplant,neuschnitt 2>/tmp/keel-gate-err \
        || deny "Tester darf nicht starten: $(cat /tmp/keel-gate-err)"
    elif [ -n "$plan" ]; then
      $FM validate "$plans/$plan.md" --type plan --status problemstellung 2>/tmp/keel-gate-err \
        || deny "Tester darf nicht starten: $(cat /tmp/keel-gate-err)"
    else
      deny "Tester braucht 'Aufgabe: <ID>' oder 'Vorhaben: <name>' im Prompt"
    fi
    ;;
  entwickler)
    [ -n "$task" ] || deny "Entwickler braucht die Zeile 'Aufgabe: <ID>' im Prompt"
    if [ "$($FM get "$tasks/$task.md" status 2>/dev/null || true)" = "reparatur" ]; then
      $FM validate "$tasks/$task.md" --type aufgabe --status reparatur 2>/tmp/keel-gate-err \
        || deny "Entwickler darf nicht starten: $(cat /tmp/keel-gate-err)"
    else
      $FM validate "$tasks/$task.md" --type aufgabe --status tests-bereit,nacharbeit --nonempty tests,dateien 2>/tmp/keel-gate-err \
        || deny "Entwickler darf nicht starten: $(cat /tmp/keel-gate-err)"
    fi
    ;;
  reviewer)
    [ -n "$task" ] || deny "Reviewer braucht die Zeile 'Aufgabe: <ID>' im Prompt"
    $FM validate "$tasks/$task.md" --type aufgabe --status review --nonempty review_runde 2>/tmp/keel-gate-err \
      || deny "Reviewer darf nicht starten: $(cat /tmp/keel-gate-err)"
    ;;
  *) deny "Unbekannte keel-Rolle '$role'" ;;
esac

sd="$(state_dir)"
printf '%s\n' "${task:-$plan}" > "$sd/pending-$role"
exit 0
