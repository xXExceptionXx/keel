#!/usr/bin/env bash
# SubagentStop: the handoff is only complete when the role's output file has the right status and
# the closing message is at most three lines. Blocks the stop otherwise. Runs the gate for the developer.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_gate_init keel-only
agent_type="$(field '.agent_type')"
role="$(keel_role "$agent_type")"
[ -n "$role" ] || keel_ok
id="$(field '.agent_id')"
proj="$(project_dir)"
keel_paths
sd="$KEEL_PATH_STATE"
ref="$(cat "$sd/agent-$id.ref" 2>/dev/null || true)"
calls="$(cat "$sd/agent-$id.calls" 2>/dev/null || echo 0)"
is_number "$calls" || calls=0
limit="$(role_limit "$role" tool_calls 60)"
is_number "$limit" || gate_fail "Werkzeugbudget für $role in .keel/config.yaml ist keine ganze Zahl: '$limit'"
msg="$(field '.last_assistant_message')"
lines="$(printf '%s\n' "$msg" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"
tasks="$proj/.keel/work/tasks"
plans="$proj/.keel/work/plans"

finish() {  # record, drop this run's state files, allow stop. The model is what actually ran, for the Coach.
  local tr; tr="$(field '.agent_transcript_path')"
  record "agent_stop" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --argjson calls "$calls" --argjson lines "$lines" --arg result "$1" --arg transcript "$tr" --arg model "$(transcript_model "$tr")" '{role:$role,agent_id:$id,ref:$ref,calls:$calls,lines:$lines,result:$result,transcript:$transcript,model:$model}')" || true
  rm -f "$sd/agent-$id.ref" "$sd/agent-$id.role" "$sd/agent-$id.calls" "$sd/agent-$id.start" "$sd/agent-$id.slow" "$sd/agent-$id.stopfail" "$sd/agent-$id.adrstand.json" "$sd/adrstand-$role.json"
  keel_ok
}

# ADRs only on the role's own level (System-ADR 0021). Before the budget shortcut: an exhausted budget must not
# carry an ADR on a foreign level past this check; tool-gate lets the role still edit .keel/adr/ to repair it.
if [ "$role" != "probe" ]; then
  snap="$sd/agent-$id.adrstand.json"
  [ -f "$snap" ] || snap="$sd/adrstand-$role.json"
  [ -f "$snap" ] || gate_fail "ADR-Stand vom Rollenstart fehlt (agent-$id.adrstand.json)"
  rc=0; out="$(python3 "$PLUGIN_ROOT/scripts/adr.py" stufe "$proj" "$snap" --role "$role" 2>"$ERRF")" || rc=$?
  case $rc in
    0) ;;
    1) block_stop "ADR auf fremder Stufe: $(printf '%s' "$out" | tr '\n' ' ')" ;;
    *) gate_fail "ADR-Stufe nicht prüfbar: $(tail -1 "$ERRF")" ;;
  esac
fi

# Tool-call budget exhausted: force the state, allow the stop so the loop ends deterministically. Time only reports.
if [ "$calls" -gt "$limit" ] && [ -n "$ref" ] && [ -f "$tasks/$ref.md" ]; then
  $FM set "$tasks/$ref.md" status=budget-erschoepft
  finish "budget-erschoepft"
fi

[ "$lines" -le 3 ] || block_stop "Abschlussnachricht hat $lines Zeilen, erlaubt sind drei. Details gehören in die Übergabe-Datei, nicht in die Nachricht."

case "$role" in
  probe) finish "ok" ;;
  planer)
    if [ -f "$tasks/$ref.md" ]; then
      # Neuschnitt: the task is re-cut in place, replaced or discarded
      $FM validate "$tasks/$ref.md" --type aufgabe --status geplant,ersetzt,verworfen 2>"$ERRF" \
        || block_stop "Neuschnitt unvollständig: $(cat "$ERRF"). Erlaubt: geplant (neu geschnitten, tests: []), ersetzt (neue Aufgaben im Plan) oder verworfen."
      st="$(fm_get "$tasks/$ref.md" status)"
      if [ "$st" = "geplant" ] && [ -n "$(fm_get "$tasks/$ref.md" tests)" ]; then
        block_stop "Neu geschnittene Aufgabe muss tests: [] haben, der Tester schreibt sie neu."
      fi
      vh="$(fm_get "$tasks/$ref.md" vorhaben)"
      [ -n "$vh" ] || block_stop "Aufgabe $ref hat kein Feld 'vorhaben'; ohne es lässt sich die Aufgabenliste des Plans nicht prüfen."
      planfile="$(fm_find "$plans" "vorhaben=$vh")"
      [ -n "$planfile" ] || block_stop "Kein Plan mit 'vorhaben: $vh' unter .keel/work/plans/; prüfe das Feld 'vorhaben' der Aufgabe $ref."
      aufgaben="$(fm_get "$planfile" aufgaben)"
      for t in $(printf '%s' "$aufgaben" | tr ',' ' '); do
        $FM validate "$tasks/$t.md" --type aufgabe --status geplant,tests-bereit,in-arbeit,fertig,review,nacharbeit --require id,vorhaben,titel 2>"$ERRF" \
          || block_stop "Plan-Aufgabenliste verweist auf unbrauchbare Aufgabe: $(cat "$ERRF"). Ersetzte und verworfene Aufgaben gehören nicht in 'aufgaben'."
      done
    else
      $FM validate "$plans/$ref.md" --type plan --status geplant --nonempty aufgaben 2>"$ERRF" \
        || block_stop "Übergabe unvollständig: $(cat "$ERRF"). Setze status: geplant und trage die Aufgaben-IDs in 'aufgaben' ein."
      aufgaben="$(fm_get "$plans/$ref.md" aufgaben)"
      for t in $(printf '%s' "$aufgaben" | tr ',' ' '); do
        $FM validate "$tasks/$t.md" --type aufgabe --status geplant --require id,vorhaben,titel --nonempty dateien,referenz 2>"$ERRF" \
          || block_stop "Aufgaben-Datei fehlt oder unvollständig: $(cat "$ERRF")"
      done
    fi
    ;;
  po)
    case "$ref" in
      epic:*)
        ep="$proj/.keel/work/epics/${ref#epic:}.md"
        $FM validate "$ep" --type epic --status skizze,bewertet,leitentscheidungen-offen,aktiv,fertig --require epic,titel,backlog 2>"$ERRF" \
          || block_stop "Epic-Datei fehlt oder unvollständig: $(cat "$ERRF")"
        st="$(fm_get "$ep" status)"
        case "$st" in
          skizze)
            for sec in "## Zielbild des Themas" "## Vorhaben" "## Leitfragen" "## Done-Condition"; do
              grep -q "^$sec" "$ep" || block_stop "Epic-Abschnitt fehlt: $sec"
            done
            ep_vh="$(fm_get "$ep" vorhaben)"
            [ -n "$ep_vh" ] || block_stop "Epic: Frontmatter 'vorhaben' ist leer; trage die Plan-Namen der Vorhaben in Reihenfolge ein"
            ;;
          bewertet) block_stop "Epic-Abstimmung nicht abgeschlossen: setze status=aktiv (alle Leitentscheidungen als ADR) oder status=leitentscheidungen-offen (Vorlagen geschrieben)" ;;
          leitentscheidungen-offen)
            ls "$proj/.keel/decisions/pending/"*epic-"${ref#epic:}"* >/dev/null 2>&1 || block_stop "status leitentscheidungen-offen ohne Vorlage unter .keel/decisions/pending/*epic-${ref#epic:}*"
            ;;
          aktiv)
            ep_le="$(fm_get "$ep" leitentscheidungen)"
            [ -n "$ep_le" ] || block_stop "status aktiv verlangt Leitentscheidungen als ADR-Nummern im Frontmatter"
            grep -q "^## Leitentscheidungen" "$ep" || block_stop "Abschnitt '## Leitentscheidungen' fehlt"
            ;;
          fertig)
            $FM validate "$ep" --nonempty abgenommen,abgenommen_von 2>/dev/null || block_stop "Epic-Abnahme braucht abgenommen=<Datum> und abgenommen_von=PO"
            ;;
        esac
        finish "ok"
        ;;
    esac
    planfile="$plans/$ref.md"
    if [ -f "$planfile" ]; then
      st="$(fm_get "$planfile" status)"
      [ -n "$st" ] || block_stop "Plan $ref hat keinen Status; setze status im Frontmatter."
      case "$st" in
        entwurf)
          $FM validate "$planfile" --type plan --require vorhaben,titel,backlog,abstimmung 2>"$ERRF" \
            || block_stop "Plan unvollständig: $(cat "$ERRF")"
          for sec in "## Problemstellung" "## Pflichtkriterien" "## Akzeptanzkriterien"; do
            grep -q "^$sec" "$planfile" || block_stop "Plan-Abschnitt fehlt: $sec"
          done
          ;;
        problemstellung)
          ab="$(fm_get "$planfile" abstimmung)"
          [ "$ab" = "einig" ] || block_stop "status problemstellung verlangt abstimmung: einig"
          ;;
        blockiert)
          ab="$(fm_get "$planfile" abstimmung)"
          [ "$ab" = "vorlage" ] || block_stop "status blockiert verlangt abstimmung: vorlage"
          ;;
        abgenommen)
          $FM validate "$planfile" --nonempty abgenommen,abgenommen_von 2>/dev/null || block_stop "Abnahme braucht abgenommen=<Datum> und abgenommen_von=PO"
          ;;
        nacharbeit)
          grep -q "^## Nacharbeit" "$planfile" || block_stop "status nacharbeit verlangt einen Abschnitt '## Nacharbeit'"
          ;;
        abnahme-bereit) block_stop "Abnahme nicht entschieden: setze status=abgenommen oder status=nacharbeit" ;;
      esac
      # Klärung: any task of this plan with a pending clarification must be answered
      for t in "$tasks"/*.md; do
        [ -f "$t" ] || continue
        grep -q "^## Klärung" "$t" || continue
        t_st="$(fm_get "$t" status)"
        if [ "$t_st" = "neuschnitt" ]; then
          k="$(fm_get "$t" klaerung)"; t_vh="$(fm_get "$t" vorhaben)"; p_vh="$(fm_get "$planfile" vorhaben)"
          [ "$k" = "beantwortet" ] || [ "$k" = "vorlage" ] || [ "$t_vh" != "$p_vh" ] \
            || block_stop "Klärung in $(basename "$t") nicht beantwortet: setze klaerung=beantwortet mit '## Antwort des PO' oder klaerung=vorlage"
        fi
      done
    else
      block_stop "Plan-Datei $planfile fehlt"
    fi
    ;;
  architekt)
    case "$ref" in
      epic:*)
        ep="$proj/.keel/work/epics/${ref#epic:}.md"
        [ -f "$ep" ] || block_stop "Epic-Datei $ep fehlt"
        st="$(fm_get "$ep" status)"
        if [ "$st" = "bewertet" ]; then
          grep -q "^## Epic-Bewertung des Architekten" "$ep" || block_stop "Abschnitt '## Epic-Bewertung des Architekten' (Kurzfassung) fehlt in der Epic-Datei"
          anl="${ep%.md}.bewertung.md"
          $FM validate "$anl" --type epic-bewertung --require epic,datum 2>"$ERRF" || block_stop "Anlage fehlt oder unvollständig: $(cat "$ERRF")"
          grep -q "Tragende Entscheidungen" "$anl" || block_stop "Anlage ohne 'Tragende Entscheidungen'"
        elif [ "$st" = "aktiv" ] || [ "$st" = "kurskorrektur" ]; then
          grep -q "^## Retrospektiven" "$ep" || block_stop "Abschnitt '## Retrospektiven' fehlt"
          [ "$st" = "kurskorrektur" ] && { grep -qi "kurskorrektur:" "$ep" || block_stop "status kurskorrektur ohne Eintrag 'kurskorrektur: …' in den Retrospektiven"; }
        else
          block_stop "Epic-Status '$st' nach Architekt unerwartet; erlaubt: bewertet (Epic-Bewertung) oder aktiv|kurskorrektur (Retrospektive)"
        fi
        finish "ok"
        ;;
      bestandsaufnahme:*|wochenrunde:*)
        modus="${ref%%:*}"; datum="${ref#*:}"
        [ "$modus" = "bestandsaufnahme" ] && rep="$proj/.keel/work/architektur/bestand-$datum.md" || rep="$proj/.keel/work/architektur/woche-$datum.md"
        $FM validate "$rep" --type architekturbericht --status passt,abweichungen --require datum,modus 2>"$ERRF" \
          || block_stop "Architekturbericht fehlt oder unvollständig ($rep): $(cat "$ERRF")"
        [ "$modus" = "bestandsaufnahme" ] && { grep -q "Referenzbeispiel" "$proj/.keel/architektur.md" || block_stop "architektur.md ohne Referenzbeispiele"; }
        if [ "$modus" = "wochenrunde" ]; then
          max_pflege="$($CFG "$proj" pflege.max_aufgaben_pro_runde 2)"
          is_number "$max_pflege" || gate_fail "pflege.max_aufgaben_pro_runde in .keel/config.yaml ist keine ganze Zahl: '$max_pflege'"
          n_pflege="$(grep -cE '^- .+ – .+ – wird Pflege' "$rep" || true)"
          [ "${n_pflege:-0}" -le "$max_pflege" ] || block_stop "Wochenrunde schlägt $n_pflege Pflegeaufgaben vor, erlaubt sind $max_pflege. Bündeln oder den Rest offen lassen."
        fi
        ;;
      *)
        planfile="$plans/$ref.md"
        [ -f "$planfile" ] || block_stop "Plan-Datei $planfile fehlt"
        st="$(fm_get "$planfile" status)"
        if [ "$st" = "entwurf" ]; then
          $FM validate "$planfile" --nonempty bewertung,abstimmung_runde 2>/dev/null || block_stop "Bewertung fehlt: setze bewertung=passt|anpassung|struktur und abstimmung_runde"
          grep -q "^## Bewertung des Architekten" "$planfile" || block_stop "Abschnitt '## Bewertung des Architekten (Runde n)' fehlt"
        else
          $FM validate "$planfile" --type plan --status abnahmetests-bereit,blockiert 2>"$ERRF" \
            || block_stop "Strukturfrage: $(cat "$ERRF"). Erlaubt: abnahmetests-bereit (Antwort) oder blockiert (ADR-Entwurf)."
          grep -q "^## Antwort des Architekten" "$planfile" || block_stop "Abschnitt '## Antwort des Architekten' fehlt"
        fi
        ;;
    esac
    ;;
  supervisor)
    vname="$(basename "$ref")"
    done_f="$proj/.keel/decisions/done/$vname"; pend_f="$proj/.keel/decisions/pending/$vname"
    if [ -f "$done_f" ]; then
      $FM validate "$done_f" --type vorlage --status entschieden --nonempty entscheidung,entschieden 2>"$ERRF" || block_stop "Entschiedene Vorlage unvollständig: $(cat "$ERRF")"
      ent="$(fm_get "$done_f" entscheider)"
      [ "$ent" = "Supervisor" ] || block_stop "Setze entscheider=Supervisor in der Vorlage"
      vorg="$(fm_get "$done_f" vorgelegt)"
      [ "$vorg" = "offen" ] || block_stop "Setze vorgelegt=offen, damit das Briefing die Entscheidung zeigt"
      grep -q "Warum nicht der Mensch" "$done_f" || block_stop "Abschnitt '## Entscheidung des Supervisors' mit 'Warum nicht der Mensch:' fehlt"
      adr="$(fm_find "$proj/.keel/adr" "vorlage=$vname")"
      [ -n "$adr" ] || block_stop "Kein ADR mit 'vorlage: $vname' unter .keel/adr/ gefunden"
    elif [ -f "$pend_f" ]; then
      esk="$(fm_get "$pend_f" eskaliert)"
      [ "$esk" = "Supervisor" ] || block_stop "Vorlage weder entschieden (nach done/ verschoben) noch eskaliert (eskaliert=Supervisor, richtungsweisend=<Grund>)"
      $FM validate "$pend_f" --nonempty richtungsweisend,eskaliert_am 2>/dev/null || block_stop "Eskalation braucht richtungsweisend=<Grund> und eskaliert_am=<Datum>"
    else
      block_stop "Vorlage $vname weder unter pending/ noch unter done/"
    fi
    ;;
  compliance)
    rep="$proj/.keel/work/compliance/$ref.md"
    $FM validate "$rep" --type compliance --status frei,auflagen,vorlage --require aufgabe,datum 2>"$ERRF" \
      || block_stop "Compliance-Datei fehlt oder unvollständig ($rep): $(cat "$ERRF")"
    [ -f "$tasks/$ref.md" ] || block_stop "Aufgabe $ref fehlt"
    t_comp="$(fm_get "$tasks/$ref.md" compliance)"; r_st="$(fm_get "$rep" status)"
    [ -n "$r_st" ] && [ "$t_comp" = "$r_st" ] || block_stop "Setze compliance=<ergebnis> in der Aufgaben-Datei, gleich dem Status der Compliance-Datei"
    ;;
  coach)
    rep="$proj/.keel/work/coach/$ref.md"
    $FM validate "$rep" --type coachbericht --require datum,kennzahlen_verletzt,vorschlaege 2>"$ERRF" \
      || block_stop "Coach-Bericht fehlt oder unvollständig ($rep): $(cat "$ERRF")"
    # Every Vorlage of the Coach says whether it concerns the project or the motor (System-ADR 0021).
    rc=0; mine="$($FM find "$proj/.keel/decisions/pending" von=Coach 2>"$ERRF")" || rc=$?
    [ "$rc" -le 1 ] || gate_fail "Vorlagen nicht lesbar: $(cat "$ERRF")"
    while IFS= read -r v; do
      [ -n "$v" ] || continue
      case "$(fm_get "$v" ebene)" in
        projekt|motor) ;;
        *) block_stop "Vorlage ${v#"$proj"/} ohne gültige ebene: setze ebene=projekt (alles unter .keel/) oder ebene=motor (Hooks, Skripte, Skills, Rollen, Standardwerte des Plugins); betrifft sie beides, teile sie." ;;
      esac
    done <<< "$mine"
    # A model switch with enough runs for a comparison must be assessed (System-ADR 0015).
    need="$($CFG "$proj" faelligkeiten.coach_nach_modellwechsel_rollenlaeufe 10)"
    is_number "$need" || need=10
    rc=0; sw_json="$(python3 "$PLUGIN_ROOT/scripts/models.py" "$proj" --json 2>"$ERRF")" || rc=$?
    [ "$rc" -eq 0 ] || gate_fail "Modellwechsel nicht prüfbar, models.py endete mit $rc: $(head -3 "$ERRF")"
    open_sw="$(printf '%s' "$sw_json" | jq -r --argjson n "$need" '[.offene_wechsel[] | select(.laeufe >= $n) | .modell] | join(", ")')"
    [ -z "$open_sw" ] || block_stop "Modellwechsel nicht bewertet: $open_sw. Vergleiche je Rolle altes und neues Modell (metrics.py, Tabelle 'Je Modell'), schreibe den Abschnitt '**Modellzuordnung:**' und setze modell_geprueft=[$open_sw] im Bericht."
    geprueft="$(fm_get "$rep" modell_geprueft)"
    if [ -n "$geprueft" ]; then
      grep -q "Modellzuordnung" "$rep" || block_stop "modell_geprueft ist gesetzt, aber der Abschnitt '**Modellzuordnung:**' fehlt im Bericht."
    fi
    ;;
  auditor)
    rep="$proj/.keel/work/audit/$ref.md"
    [ -f "$proj/.keel/work/audit/woche-$ref.md" ] && [ ! -f "$rep" ] && rep="$proj/.keel/work/audit/woche-$ref.md"
    $FM validate "$rep" --type pruefbericht --status passt,abweichungen --require datum,modus,seit 2>"$ERRF" \
      || block_stop "Prüfbericht fehlt oder unvollständig ($rep): $(cat "$ERRF"). Pflichtfelder: typ pruefbericht, datum, modus, seit, status passt|abweichungen."
    ;;
  tester)
    if [ -f "$tasks/$ref.md" ]; then
      $FM validate "$tasks/$ref.md" --type aufgabe --status tests-bereit --nonempty tests 2>"$ERRF" \
        || block_stop "Übergabe unvollständig: $(cat "$ERRF"). Setze status: tests-bereit und liste die Testdateien in 'tests'."
    else
      $FM validate "$plans/$ref.md" --type plan --status abnahmetests-bereit --nonempty abnahmetests 2>"$ERRF" \
        || block_stop "Übergabe unvollständig: $(cat "$ERRF"). Setze status: abnahmetests-bereit und liste die Testdateien in 'abnahmetests'."
    fi
    ;;
  entwickler)
    $FM validate "$tasks/$ref.md" --type aufgabe --status fertig-gemeldet,testeinspruch 2>"$ERRF" \
      || block_stop "Übergabe unvollständig: $(cat "$ERRF"). Erlaubt: fertig-gemeldet (mit nachweis) oder testeinspruch (mit begruendung)."
    status="$(fm_get "$tasks/$ref.md" status)"
    if [ "$status" = "fertig-gemeldet" ]; then
      $FM validate "$tasks/$ref.md" --nonempty nachweis 2>/dev/null || block_stop "Feld 'nachweis' fehlt: trage die Testausgabe in Kurzform ein."
      out="$(bash "$PLUGIN_ROOT/scripts/gate.sh" "$proj" "$ref" 2>&1)" || block_stop "Prüftor rot. $out"
      excl=(':(exclude).keel')
      tests="$(fm_get "$tasks/$ref.md" tests)"
      for t in $(printf '%s' "$tests" | tr ',' ' '); do excl+=(":(exclude)$t"); done
      git -C "$proj" rev-parse -q --verify HEAD >/dev/null || block_stop "Repository ohne Commit: der Diff der Aufgabe lässt sich nicht messen. Lege einen ersten Commit an."
      diff_lines="$(cd "$proj" && git diff --numstat HEAD -- . "${excl[@]}" | awk '{s+=$1+$2} END {print s+0}')"
      max_diff="$($CFG "$proj" budget.diff_lines 300)"
      is_number "$max_diff" || gate_fail "budget.diff_lines in .keel/config.yaml ist keine ganze Zahl: '$max_diff'"
      [ "$diff_lines" -le "$max_diff" ] || block_stop "Diff hat $diff_lines Zeilen, erlaubt sind $max_diff. Setze status: budget-erschoepft und beschreibe den Stand, der Planer schneidet neu."
      # Compliance scan: secrets block, new dependencies and personal data are recorded for the Lead
      rc=0; scan="$(python3 "$PLUGIN_ROOT/scripts/compliance_scan.py" "$proj" 2>&1)" || rc=$?
      case $rc in
        0|3|4|5) ;;
        *) block_stop "Compliance-Scan fehlgeschlagen (Code $rc), die Aufgabe ist ungeprüft: $(printf '%s' "$scan" | tail -3 | tr '\n' ' ')/keel:hilfe erklärt den Stand." ;;
      esac
      mkdir -p "$proj/.keel/work/compliance"
      printf -- '---\ntyp: compliance-scan\naufgabe: %s\ndatum: %s\nergebnis: %s\n---\n\n```\n%s\n```\n' "$ref" "$(date +%F)" "$(printf '%s' "$scan" | head -1 | sed -E 's/^compliance: ([a-z]+).*/\1/')" "$scan" > "$proj/.keel/work/compliance/$ref.scan.md"
      case $rc in
        5) block_stop "Compliance blockiert: Secret, Stub (TODO, not implemented) oder übersprungener Test im Diff. Eine Aufgabe ist fertig oder nicht; Platzhalter gehören als Testeinspruch oder Stand in die Aufgaben-Datei. $(printf '%s' "$scan" | grep -F '[block]' | head -3 | tr '\n' ' ')" ;;
        4) $FM set "$tasks/$ref.md" compliance=vorlage ;;
        3) $FM set "$tasks/$ref.md" compliance=pruefen ;;
        0) $FM set "$tasks/$ref.md" compliance=frei ;;
      esac
    else
      $FM validate "$tasks/$ref.md" --nonempty begruendung 2>/dev/null || block_stop "Testeinspruch braucht das Feld 'begruendung'."
    fi
    ;;
  reviewer)
    runde="$(fm_get "$tasks/$ref.md" review_runde)"
    [ -n "$runde" ] || block_stop "Aufgabe $ref hat kein Feld 'review_runde'; ohne es ist die Review-Datei nicht zuzuordnen."
    rev="$proj/.keel/work/reviews/$ref-r$runde.md"
    $FM validate "$rev" --type review --status bestanden,befunde --require aufgabe,runde 2>"$ERRF" \
      || block_stop "Review-Datei fehlt oder unvollständig ($rev): $(cat "$ERRF")"
    # Threshold and trend are computed, not judged; the Lead reads review_ergebnis (System-ADR 0018)
    python3 "$PLUGIN_ROOT/scripts/review.py" pruefen "$proj" "$ref" >/dev/null 2>"$ERRF" \
      || block_stop "Review ungültig: $(cat "$ERRF")"
    rev_st="$(fm_get "$rev" status)"
    [ "$rev_st" = "bestanden" ] && python3 "$PLUGIN_ROOT/scripts/pflege.py" sammeln "$proj" "$rev" >/dev/null 2>&1 || true
    ;;
esac
finish "ok"
