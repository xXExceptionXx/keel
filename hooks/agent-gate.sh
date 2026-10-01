#!/usr/bin/env bash
# PreToolUse on Agent: a keel role may only start when its input handoff exists and has the right status.
# Also parks the task or plan reference so SubagentStart can bind it to the agent id.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_gate_init keel-only

type="$(field '.tool_input.subagent_type')"
role="$(keel_role "$type")"
[ -n "$role" ] || keel_ok

# Entry conditions (status and nonempty lists per role and occasion) and due-item roles come from
# scripts/flow.py, the same table the monitor reads. Fail closed: without it no role starts.
eval "$(python3 "$PLUGIN_ROOT/scripts/flow.py" shell 2>/dev/null)" || true
[ -n "${KEEL_S_tester_aufgabe:-}" ] || deny "keel: Ablaufregeln (scripts/flow.py) nicht lesbar; keine Rolle startet. /keel:hilfe meldet den Motor-Befund."

# keel roles run sequentially and in the foreground: the Lead must see the result before it continues,
# and the reference parking below relies on one start at a time.
if [ "$(field '.tool_input.run_in_background')" = "true" ]; then
  deny "keel-Rollen laufen im Vordergrund und nacheinander. Starte '$type' erneut mit run_in_background: false."
fi
sd_early="$(state_dir)"
# A helper session (/keel:hilfe) only observes; roles run in a fresh session.
sid="$(field '.session_id')"
if [ -n "$sid" ] && [ -f "$sd_early/hilfe-$sid" ]; then
  deny "Diese Session ist eine Hilfe-Session (/keel:hilfe) und beobachtet nur. Rollen arbeiten in einer neuen Session mit /keel:start."
fi
if [ -f "$sd_early/pending-$role" ]; then
  mtime="$(stat -c %Y "$sd_early/pending-$role" 2>/dev/null || stat -f %m "$sd_early/pending-$role" 2>/dev/null || true)"
  age=600
  if is_number "$mtime"; then age=$(( $(date +%s) - mtime )); fi
  if [ "$age" -lt 600 ]; then
    deny "Rolle '$role' wurde vor $age Sekunden bereits gestartet und läuft noch. keel arbeitet sequenziell; warte auf ihr Ergebnis. Läuft nichts mehr: /keel:hilfe zeigt und räumt Reste auf."
  fi
fi

# Due gate: while something hard is due, only the roles that satisfy it may run.
due_json="$(python3 "$PLUGIN_ROOT/scripts/due.py" "$(project_dir)" --json 2>/dev/null || true)"
if [ -n "$due_json" ] && [ "$(printf '%s' "$due_json" | jq -r '.hart')" = "true" ]; then
  allowed=""
  for art in $(printf '%s' "$due_json" | jq -r '.faellig[] | select(.hart) | .art'); do
    var="KEEL_DUE_${art//[^A-Za-z0-9]/_}"
    allowed="$allowed ${!var:-}"
  done
  case " $allowed " in
    *" $role "*) ;;
    *) deny "Fällig, bevor Rollen arbeiten: $(printf '%s' "$due_json" | jq -r '[.faellig[] | select(.hart) | .art + " (" + .grund + ")"] | join("; ")'). Starte /keel:start, es arbeitet die Fälligkeiten in Reihenfolge ab. Unklar, was los ist: /keel:hilfe erklärt den Stand." ;;
  esac
fi

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
      $FM validate "$tasks/$task.md" --type aufgabe --status "$KEEL_S_planer_neuschnitt" 2>"$ERRF" \
        || deny "Planer (Neuschnitt) darf nicht starten: $(cat "$ERRF")"
    else
      [ -n "$plan" ] || deny "Planer braucht die Zeile 'Vorhaben: <name>' oder 'Aufgabe: <ID>' im Prompt"
      $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_planer_planung" 2>"$ERRF" \
        || deny "Planer darf nicht starten: $(cat "$ERRF"). Erst der Tester mit Abnahmetests."
    fi
    ;;
  po)
    anlass="$(prompt_field "$prompt" "Anlass")"
    epic="$(prompt_field "$prompt" "Epic")"
    epics="$proj/.keel/work/epics"
    case "$anlass" in
      epic-skizze)
        [ -n "$epic" ] && [ -n "$(prompt_field "$prompt" "Backlog")" ] || deny "PO (epic-skizze) braucht 'Epic: <name>' und 'Backlog: <id>'"
        [ ! -f "$epics/$epic.md" ] || deny "PO (epic-skizze): Epic existiert schon"
        plan="epic:$epic"
        ;;
      epic-abstimmung)
        [ -n "$epic" ] || deny "PO (epic-abstimmung) braucht 'Epic: <name>'"
        $FM validate "$epics/$epic.md" --type epic --status "$KEEL_S_po_epic_abstimmung" 2>"$ERRF" \
          || deny "PO (epic-abstimmung) darf nicht starten: $(cat "$ERRF"). Erst der Architekt mit Epic-Bewertung."
        plan="epic:$epic"
        ;;
      epic-abnahme)
        [ -n "$epic" ] || deny "PO (epic-abnahme) braucht 'Epic: <name>'"
        $FM validate "$epics/$epic.md" --type epic --status "$KEEL_S_po_epic_abnahme" 2>"$ERRF" \
          || deny "PO (epic-abnahme) darf nicht starten: $(cat "$ERRF")"
        plan="epic:$epic"
        ;;
    esac
    [ -n "$plan" ] || deny "PO braucht die Zeile 'Vorhaben: <name>' im Prompt"
    case "$anlass" in
      epic-skizze|epic-abstimmung|epic-abnahme) ;;
      problemstellung)
        [ -n "$(prompt_field "$prompt" "Backlog")" ] || deny "PO (problemstellung) braucht die Zeile 'Backlog: <id>'"
        [ ! -f "$plans/$plan.md" ] || $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_po_problemstellung" 2>"$ERRF" \
          || deny "PO (problemstellung): Plan existiert schon: $(cat "$ERRF")"
        ;;
      abstimmung)
        $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_po_abstimmung" --nonempty "$KEEL_N_po_abstimmung" 2>"$ERRF" \
          || deny "PO (abstimmung) darf nicht starten: $(cat "$ERRF"). Erst der Architekt mit Bewertung."
        ;;
      klaerung)
        [ -n "$task" ] || deny "PO (klaerung) braucht die Zeile 'Aufgabe: <ID>'"
        $FM validate "$tasks/$task.md" --type aufgabe --status "$KEEL_S_po_klaerung" 2>"$ERRF" \
          || deny "PO (klaerung) darf nicht starten: $(cat "$ERRF")"
        grep -q "^## Klärung" "$tasks/$task.md" || deny "PO (klaerung): Aufgabe hat keinen Abschnitt '## Klärung'"
        ;;
      abnahme)
        $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_po_abnahme" 2>"$ERRF" \
          || deny "PO (abnahme) darf nicht starten: $(cat "$ERRF")"
        [ -f "$proj/.keel/work/acceptance/$plan.md" ] || deny "PO (abnahme): Abnahmenachweis fehlt"
        ;;
      *) deny "PO braucht 'Anlass: problemstellung | abstimmung | klaerung | abnahme | epic-skizze | epic-abstimmung | epic-abnahme'" ;;
    esac
    task="$plan"
    ;;
  architekt)
    anlass="$(prompt_field "$prompt" "Anlass")"
    epic="$(prompt_field "$prompt" "Epic")"
    epics="$proj/.keel/work/epics"
    case "$anlass" in
      epic-bewertung)
        [ -n "$epic" ] || deny "Architekt (epic-bewertung) braucht 'Epic: <name>'"
        $FM validate "$epics/$epic.md" --type epic --status "$KEEL_S_architekt_epic_bewertung" 2>"$ERRF" \
          || deny "Architekt (epic-bewertung) darf nicht starten: $(cat "$ERRF")"
        task="epic:$epic"
        ;;
      epic-retrospektive)
        [ -n "$epic" ] && [ -n "$plan" ] || deny "Architekt (epic-retrospektive) braucht 'Epic: <name>' und 'Vorhaben: <name>'"
        $FM validate "$epics/$epic.md" --type epic --status "$KEEL_S_architekt_epic_retrospektive" 2>"$ERRF" \
          || deny "Architekt (epic-retrospektive) darf nicht starten: $(cat "$ERRF")"
        $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_architekt_epic_retrospektive_vorhaben" 2>"$ERRF" \
          || deny "Architekt (epic-retrospektive): Vorhaben nicht integriert: $(cat "$ERRF")"
        task="epic:$epic"
        ;;
      bewertung)
        [ -n "$plan" ] || deny "Architekt (bewertung) braucht 'Vorhaben: <name>'"
        $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_architekt_bewertung" 2>"$ERRF" \
          || deny "Architekt (bewertung) darf nicht starten: $(cat "$ERRF")"
        task="$plan"
        ;;
      strukturfrage)
        [ -n "$plan" ] || deny "Architekt (strukturfrage) braucht 'Vorhaben: <name>'"
        $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_architekt_strukturfrage" 2>"$ERRF" \
          || deny "Architekt (strukturfrage) darf nicht starten: $(cat "$ERRF")"
        task="$plan"
        ;;
      bestandsaufnahme|wochenrunde)
        datum="$(prompt_field "$prompt" "Datum")"
        [ -n "$datum" ] || deny "Architekt ($anlass) braucht 'Datum: YYYY-MM-DD'"
        task="$anlass:$datum"
        ;;
      *) deny "Architekt braucht 'Anlass: bewertung | strukturfrage | bestandsaufnahme | wochenrunde | epic-bewertung | epic-retrospektive'" ;;
    esac
    ;;
  compliance)
    [ -n "$task" ] || deny "Compliance braucht die Zeile 'Aufgabe: <ID>' im Prompt"
    [ "$($FM get "$tasks/$task.md" compliance 2>/dev/null || true)" = "pruefen" ] || deny "Compliance darf nicht starten: Aufgabe hat nicht compliance: pruefen"
    [ -f "$proj/.keel/work/compliance/$task.scan.md" ] || deny "Compliance: Scan-Datei fehlt"
    ;;
  supervisor)
    anlass="$(prompt_field "$prompt" "Anlass")"
    [ "$anlass" = "entscheiden" ] || deny "Supervisor braucht 'Anlass: entscheiden'"
    vfile="$({ printf '%s' "$prompt" | grep -oE '^Vorlage:[[:space:]]*[^[:space:]]+' || true; } | head -1 | sed -E 's/^Vorlage:[[:space:]]*//')"
    [ -n "$vfile" ] || deny "Supervisor braucht 'Vorlage: <pfad>'"
    [ -f "$proj/$vfile" ] || deny "Supervisor: Vorlage $vfile existiert nicht"
    $FM validate "$proj/$vfile" --type vorlage --status "$KEEL_S_supervisor_entscheiden" 2>"$ERRF" || deny "Supervisor: $(cat "$ERRF")"
    [ -z "$($FM get "$proj/$vfile" eskaliert 2>/dev/null || true)" ] || deny "Supervisor: Vorlage ist bereits an den Menschen eskaliert"
    task="$vfile"
    ;;
  auditor|coach)
    datum="$(prompt_field "$prompt" "Datum")"
    [ -n "$datum" ] || deny "$role braucht die Zeile 'Datum: YYYY-MM-DD' im Prompt"
    task="$datum"
    ;;
  tester)
    if [ -n "$task" ]; then
      $FM validate "$tasks/$task.md" --type aufgabe --status "$KEEL_S_tester_aufgabe" 2>"$ERRF" \
        || deny "Tester darf nicht starten: $(cat "$ERRF")"
    elif [ -n "$plan" ]; then
      $FM validate "$plans/$plan.md" --type plan --status "$KEEL_S_tester_abnahmetests" 2>"$ERRF" \
        || deny "Tester darf nicht starten: $(cat "$ERRF")"
    else
      deny "Tester braucht 'Aufgabe: <ID>' oder 'Vorhaben: <name>' im Prompt"
    fi
    ;;
  entwickler)
    [ -n "$task" ] || deny "Entwickler braucht die Zeile 'Aufgabe: <ID>' im Prompt"
    if [ "$($FM get "$tasks/$task.md" status 2>/dev/null || true)" = "reparatur" ] || [ "$($FM get "$tasks/$task.md" vorhaben 2>/dev/null || true)" = "R" ]; then
      # Repair tasks have no tests of their own; rework after a review is allowed (System-ADR 0018)
      $FM validate "$tasks/$task.md" --type aufgabe --status "$KEEL_S_entwickler_reparatur" 2>"$ERRF" \
        || deny "Entwickler darf nicht starten: $(cat "$ERRF")"
    else
      $FM validate "$tasks/$task.md" --type aufgabe --status "$KEEL_S_entwickler_aufgabe" --nonempty "$KEEL_N_entwickler_aufgabe" 2>"$ERRF" \
        || deny "Entwickler darf nicht starten: $(cat "$ERRF")"
    fi
    ;;
  reviewer)
    [ -n "$task" ] || deny "Reviewer braucht die Zeile 'Aufgabe: <ID>' im Prompt"
    $FM validate "$tasks/$task.md" --type aufgabe --status "$KEEL_S_reviewer_aufgabe" --nonempty "$KEEL_N_reviewer_aufgabe" 2>"$ERRF" \
      || deny "Reviewer darf nicht starten: $(cat "$ERRF")"
    # Snapshot of this round, so the next round can review the rework on its own (System-ADR 0018)
    python3 "$PLUGIN_ROOT/scripts/review.py" stand "$proj" "$task" >/dev/null 2>"$ERRF" \
      || deny "Reviewer: Stand der Runde nicht festgehalten: $(cat "$ERRF")"
    ;;
  *) deny "Unbekannte keel-Rolle '$role'" ;;
esac

sd="$(state_dir)"
printf '%s\n' "${task:-$plan}" > "$sd/pending-$role"
keel_ok
