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

# Budget exhausted (calls or time): force the state, allow the stop so the loop ends deterministically.
if { [ "$calls" -gt "$limit" ] || [ -f "$sd/agent-$id.timeout" ]; } && [ -n "$ref" ] && [ -f "$tasks/$ref.md" ]; then
  $FM set "$tasks/$ref.md" status=budget-erschoepft
  finish "budget-erschoepft"
fi

[ "$lines" -le 3 ] || block_stop "Abschlussnachricht hat $lines Zeilen, erlaubt sind drei. Details gehören in die Übergabe-Datei, nicht in die Nachricht."

case "$role" in
  probe) finish "ok" ;;
  planer)
    if [ -f "$tasks/$ref.md" ]; then
      # Neuschnitt: the task is re-cut in place, replaced or discarded
      $FM validate "$tasks/$ref.md" --type aufgabe --status geplant,ersetzt,verworfen 2>/tmp/keel-stop-err \
        || block_stop "Neuschnitt unvollständig: $(cat /tmp/keel-stop-err). Erlaubt: geplant (neu geschnitten, tests: []), ersetzt (neue Aufgaben im Plan) oder verworfen."
      st="$($FM get "$tasks/$ref.md" status)"
      [ "$st" = "geplant" ] && [ -n "$($FM get "$tasks/$ref.md" tests 2>/dev/null || true)" ] && block_stop "Neu geschnittene Aufgabe muss tests: [] haben, der Tester schreibt sie neu."
      vh="$($FM get "$tasks/$ref.md" vorhaben)"
      planfile="$(grep -l "^vorhaben: $vh$" "$plans"/*.md | head -1)"
      for t in $($FM get "$planfile" aufgaben | tr ',' ' '); do
        $FM validate "$tasks/$t.md" --type aufgabe --status geplant,tests-bereit,in-arbeit,fertig,review,nacharbeit --require id,vorhaben,titel 2>/tmp/keel-stop-err \
          || block_stop "Plan-Aufgabenliste verweist auf unbrauchbare Aufgabe: $(cat /tmp/keel-stop-err). Ersetzte und verworfene Aufgaben gehören nicht in 'aufgaben'."
      done
    else
      $FM validate "$plans/$ref.md" --type plan --status geplant --nonempty aufgaben 2>/tmp/keel-stop-err \
        || block_stop "Übergabe unvollständig: $(cat /tmp/keel-stop-err). Setze status: geplant und trage die Aufgaben-IDs in 'aufgaben' ein."
      for t in $($FM get "$plans/$ref.md" aufgaben | tr ',' ' '); do
        $FM validate "$tasks/$t.md" --type aufgabe --status geplant --require id,vorhaben,titel --nonempty dateien,referenz 2>/tmp/keel-stop-err \
          || block_stop "Aufgaben-Datei fehlt oder unvollständig: $(cat /tmp/keel-stop-err)"
      done
    fi
    ;;
  auditor)
    rep="$proj/.keel/work/audit/$ref.md"
    [ -f "$proj/.keel/work/audit/woche-$ref.md" ] && [ ! -f "$rep" ] && rep="$proj/.keel/work/audit/woche-$ref.md"
    $FM validate "$rep" --type pruefbericht --status passt,abweichungen --require datum,modus,seit 2>/tmp/keel-stop-err \
      || block_stop "Prüfbericht fehlt oder unvollständig ($rep): $(cat /tmp/keel-stop-err). Pflichtfelder: typ pruefbericht, datum, modus, seit, status passt|abweichungen."
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
