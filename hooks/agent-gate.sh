#!/usr/bin/env bash
# PreToolUse on Agent: a keel role may only start when its input handoff exists and has the right status.
# Also parks the task or plan reference so SubagentStart can bind it to the agent id.
set -euo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

type="$(field '.tool_input.subagent_type')"
role="$(keel_role "$type")"
[ -z "$role" ] && exit 0

# keel roles run sequentially and in the foreground: the Lead must see the result before it continues,
# and the reference parking below relies on one start at a time.
if [ "$(field '.tool_input.run_in_background')" = "true" ]; then
  deny "keel-Rollen laufen im Vordergrund und nacheinander. Starte '$type' erneut mit run_in_background: false."
fi
sd_early="$(state_dir)"
if [ -f "$sd_early/pending-$role" ]; then
  age=$(( $(date +%s) - $(stat -f %m "$sd_early/pending-$role" 2>/dev/null || stat -c %Y "$sd_early/pending-$role") ))
  if [ "$age" -lt 600 ]; then
    deny "Rolle '$role' wurde vor $age Sekunden bereits gestartet und läuft noch. keel arbeitet sequenziell; warte auf ihr Ergebnis."
  fi
fi

# Briefing gate: while a Supervisor briefing is due, only the Supervisor may run.
if [ "$role" != "supervisor" ]; then
  reasons="$(python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$(project_dir)" 2>/dev/null)" || deny "Briefing mit dem Supervisor nötig, bevor Rollen arbeiten: /keel:briefing. $reasons"
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
      $FM validate "$tasks/$task.md" --type aufgabe --status neuschnitt 2>/tmp/keel-gate-err \
        || deny "Planer (Neuschnitt) darf nicht starten: $(cat /tmp/keel-gate-err)"
    else
      [ -n "$plan" ] || deny "Planer braucht die Zeile 'Vorhaben: <name>' oder 'Aufgabe: <ID>' im Prompt"
      $FM validate "$plans/$plan.md" --type plan --status abnahmetests-bereit,nacharbeit 2>/tmp/keel-gate-err \
        || deny "Planer darf nicht starten: $(cat /tmp/keel-gate-err). Erst der Tester mit Abnahmetests."
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
        $FM validate "$epics/$epic.md" --type epic --status bewertet,leitentscheidungen-offen 2>/tmp/keel-gate-err \
          || deny "PO (epic-abstimmung) darf nicht starten: $(cat /tmp/keel-gate-err). Erst der Architekt mit Epic-Bewertung."
        plan="epic:$epic"
        ;;
      epic-abnahme)
        [ -n "$epic" ] || deny "PO (epic-abnahme) braucht 'Epic: <name>'"
        $FM validate "$epics/$epic.md" --type epic --status aktiv 2>/tmp/keel-gate-err \
          || deny "PO (epic-abnahme) darf nicht starten: $(cat /tmp/keel-gate-err)"
        plan="epic:$epic"
        ;;
    esac
    [ -n "$plan" ] || deny "PO braucht die Zeile 'Vorhaben: <name>' im Prompt"
    case "$anlass" in
      epic-skizze|epic-abstimmung|epic-abnahme) ;;
      problemstellung)
        [ -n "$(prompt_field "$prompt" "Backlog")" ] || deny "PO (problemstellung) braucht die Zeile 'Backlog: <id>'"
        [ ! -f "$plans/$plan.md" ] || $FM validate "$plans/$plan.md" --type plan --status entwurf 2>/tmp/keel-gate-err \
          || deny "PO (problemstellung): Plan existiert schon: $(cat /tmp/keel-gate-err)"
        ;;
      abstimmung)
        $FM validate "$plans/$plan.md" --type plan --status entwurf --nonempty bewertung 2>/tmp/keel-gate-err \
          || deny "PO (abstimmung) darf nicht starten: $(cat /tmp/keel-gate-err). Erst der Architekt mit Bewertung."
        ;;
      klaerung)
        [ -n "$task" ] || deny "PO (klaerung) braucht die Zeile 'Aufgabe: <ID>'"
        $FM validate "$tasks/$task.md" --type aufgabe --status neuschnitt 2>/tmp/keel-gate-err \
          || deny "PO (klaerung) darf nicht starten: $(cat /tmp/keel-gate-err)"
        grep -q "^## Klärung" "$tasks/$task.md" || deny "PO (klaerung): Aufgabe hat keinen Abschnitt '## Klärung'"
        ;;
      abnahme)
        $FM validate "$plans/$plan.md" --type plan --status abnahme-bereit 2>/tmp/keel-gate-err \
          || deny "PO (abnahme) darf nicht starten: $(cat /tmp/keel-gate-err)"
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
        $FM validate "$epics/$epic.md" --type epic --status skizze 2>/tmp/keel-gate-err \
          || deny "Architekt (epic-bewertung) darf nicht starten: $(cat /tmp/keel-gate-err)"
        task="epic:$epic"
        ;;
      epic-retrospektive)
        [ -n "$epic" ] && [ -n "$plan" ] || deny "Architekt (epic-retrospektive) braucht 'Epic: <name>' und 'Vorhaben: <name>'"
        $FM validate "$epics/$epic.md" --type epic --status aktiv 2>/tmp/keel-gate-err \
          || deny "Architekt (epic-retrospektive) darf nicht starten: $(cat /tmp/keel-gate-err)"
        $FM validate "$plans/$plan.md" --type plan --status integriert 2>/tmp/keel-gate-err \
          || deny "Architekt (epic-retrospektive): Vorhaben nicht integriert: $(cat /tmp/keel-gate-err)"
        task="epic:$epic"
        ;;
      bewertung)
        [ -n "$plan" ] || deny "Architekt (bewertung) braucht 'Vorhaben: <name>'"
        $FM validate "$plans/$plan.md" --type plan --status entwurf 2>/tmp/keel-gate-err \
          || deny "Architekt (bewertung) darf nicht starten: $(cat /tmp/keel-gate-err)"
        task="$plan"
        ;;
      strukturfrage)
        [ -n "$plan" ] || deny "Architekt (strukturfrage) braucht 'Vorhaben: <name>'"
        $FM validate "$plans/$plan.md" --type plan --status strukturaenderung 2>/tmp/keel-gate-err \
          || deny "Architekt (strukturfrage) darf nicht starten: $(cat /tmp/keel-gate-err)"
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
    $FM validate "$proj/$vfile" --type vorlage --status offen 2>/tmp/keel-gate-err || deny "Supervisor: $(cat /tmp/keel-gate-err)"
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
