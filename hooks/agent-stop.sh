#!/usr/bin/env bash
# SubagentStop: the handoff is only complete when the role's output file has the right status and
# the closing message is at most three lines. Blocks the stop otherwise. Runs the gate for the developer.
set -euo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
role="$(keel_role "$(field '.agent_type')")"
[ -z "$role" ] && exit 0
id="$(field '.agent_id')"
proj="$(project_dir)"
sd="$(state_dir)"
ref="$(cat "$sd/agent-$id.ref" 2>/dev/null || true)"
calls="$(cat "$sd/agent-$id.calls" 2>/dev/null || echo 0)"
limit="$($CFG "$proj" budget.tool_calls 60)"
msg="$(field '.last_assistant_message')"
lines="$(printf '%s\n' "$msg" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"
tasks="$proj/.keel/work/tasks"
plans="$proj/.keel/work/plans"

finish() {  # record and allow stop
  record "agent_stop" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --argjson calls "$calls" --argjson lines "$lines" --arg result "$1" '{role:$role,agent_id:$id,ref:$ref,calls:$calls,lines:$lines,result:$result}')"
  exit 0
}

# Budget exhausted: force the state, allow the stop so the loop ends deterministically.
if [ "$calls" -gt "$limit" ] && [ -n "$ref" ] && [ -f "$tasks/$ref.md" ]; then
  $FM set "$tasks/$ref.md" status=budget-erschoepft
  finish "budget-erschoepft"
fi

[ "$lines" -le 3 ] || block_stop "Abschlussnachricht hat $lines Zeilen, erlaubt sind drei. Details gehören in die Übergabe-Datei, nicht in die Nachricht."

case "$role" in
  probe) finish "ok" ;;
  planer)
    $FM validate "$plans/$ref.md" --type plan --status geplant --nonempty aufgaben 2>/tmp/keel-stop-err \
      || block_stop "Übergabe unvollständig: $(cat /tmp/keel-stop-err). Setze status: geplant und trage die Aufgaben-IDs in 'aufgaben' ein."
    for t in $($FM get "$plans/$ref.md" aufgaben | tr ',' ' '); do
      $FM validate "$tasks/$t.md" --type aufgabe --status geplant --require id,vorhaben,titel --nonempty dateien,referenz 2>/tmp/keel-stop-err \
        || block_stop "Aufgaben-Datei fehlt oder unvollständig: $(cat /tmp/keel-stop-err)"
    done
    ;;
  tester)
    if [ -f "$tasks/$ref.md" ]; then
      $FM validate "$tasks/$ref.md" --type aufgabe --status tests-bereit --nonempty tests 2>/tmp/keel-stop-err \
        || block_stop "Übergabe unvollständig: $(cat /tmp/keel-stop-err). Setze status: tests-bereit und liste die Testdateien in 'tests'."
    else
      $FM validate "$plans/$ref.md" --type plan --status abnahmetests-bereit --nonempty abnahmetests 2>/tmp/keel-stop-err \
        || block_stop "Übergabe unvollständig: $(cat /tmp/keel-stop-err). Setze status: abnahmetests-bereit und liste die Testdateien in 'abnahmetests'."
    fi
    ;;
  entwickler)
    $FM validate "$tasks/$ref.md" --type aufgabe --status fertig-gemeldet,testeinspruch 2>/tmp/keel-stop-err \
      || block_stop "Übergabe unvollständig: $(cat /tmp/keel-stop-err). Erlaubt: fertig-gemeldet (mit nachweis) oder testeinspruch (mit begruendung)."
    status="$($FM get "$tasks/$ref.md" status)"
    if [ "$status" = "fertig-gemeldet" ]; then
      $FM validate "$tasks/$ref.md" --nonempty nachweis 2>/dev/null || block_stop "Feld 'nachweis' fehlt: trage die Testausgabe in Kurzform ein."
      out="$(bash "$PLUGIN_ROOT/scripts/gate.sh" "$proj" "$ref" 2>&1)" || block_stop "Prüftor rot. $out"
      excl=(':(exclude).keel')
      for t in $($FM get "$tasks/$ref.md" tests | tr ',' ' '); do excl+=(":(exclude)$t"); done
      diff_lines="$(cd "$proj" && git diff --numstat HEAD -- . "${excl[@]}" | awk '{s+=$1+$2} END {print s+0}')"
      max_diff="$($CFG "$proj" budget.diff_lines 300)"
      [ "$diff_lines" -le "$max_diff" ] || block_stop "Diff hat $diff_lines Zeilen, erlaubt sind $max_diff. Setze status: budget-erschoepft und beschreibe den Stand, der Planer schneidet neu."
    else
      $FM validate "$tasks/$ref.md" --nonempty begruendung 2>/dev/null || block_stop "Testeinspruch braucht das Feld 'begruendung'."
    fi
    ;;
  reviewer)
    runde="$($FM get "$tasks/$ref.md" review_runde)"
    rev="$proj/.keel/work/reviews/$ref-r$runde.md"
    $FM validate "$rev" --type review --status bestanden,befunde --require aufgabe,runde 2>/tmp/keel-stop-err \
      || block_stop "Review-Datei fehlt oder unvollständig ($rev): $(cat /tmp/keel-stop-err)"
    ;;
esac
finish "ok"
