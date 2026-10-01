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
sd="$(state_dir)"
ref="$(cat "$sd/agent-$id.ref" 2>/dev/null || true)"
calls="$(cat "$sd/agent-$id.calls" 2>/dev/null || echo 0)"
is_number "$calls" || calls=0
limit="$(role_limit "$role" tool_calls 60)"
msg="$(field '.last_assistant_message')"
lines="$(printf '%s\n' "$msg" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')"
tasks="$proj/.keel/work/tasks"
plans="$proj/.keel/work/plans"

finish() {  # record, drop this run's state files, allow stop. The model is what actually ran, for the Coach.
  local tr; tr="$(field '.agent_transcript_path')"
  record "agent_stop" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --argjson calls "$calls" --argjson lines "$lines" --arg result "$1" --arg transcript "$tr" --arg model "$(transcript_model "$tr")" '{role:$role,agent_id:$id,ref:$ref,calls:$calls,lines:$lines,result:$result,transcript:$transcript,model:$model}')" || true
  rm -f "$sd/agent-$id.ref" "$sd/agent-$id.role" "$sd/agent-$id.calls" "$sd/agent-$id.start" "$sd/agent-$id.timeout"
  keel_ok
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
      $FM validate "$tasks/$ref.md" --type aufgabe --status geplant,ersetzt,verworfen 2>"$ERRF" \
        || block_stop "Neuschnitt unvollständig: $(cat "$ERRF"). Erlaubt: geplant (neu geschnitten, tests: []), ersetzt (neue Aufgaben im Plan) oder verworfen."
      st="$($FM get "$tasks/$ref.md" status)"
      [ "$st" = "geplant" ] && [ -n "$($FM get "$tasks/$ref.md" tests 2>/dev/null || true)" ] && block_stop "Neu geschnittene Aufgabe muss tests: [] haben, der Tester schreibt sie neu."
      vh="$($FM get "$tasks/$ref.md" vorhaben)"
      planfile="$(grep -l "^vorhaben: $vh$" "$plans"/*.md | head -1)"
      for t in $($FM get "$planfile" aufgaben | tr ',' ' '); do
        $FM validate "$tasks/$t.md" --type aufgabe --status geplant,tests-bereit,in-arbeit,fertig,review,nacharbeit --require id,vorhaben,titel 2>"$ERRF" \
          || block_stop "Plan-Aufgabenliste verweist auf unbrauchbare Aufgabe: $(cat "$ERRF"). Ersetzte und verworfene Aufgaben gehören nicht in 'aufgaben'."
      done
    else
      $FM validate "$plans/$ref.md" --type plan --status geplant --nonempty aufgaben 2>"$ERRF" \
        || block_stop "Übergabe unvollständig: $(cat "$ERRF"). Setze status: geplant und trage die Aufgaben-IDs in 'aufgaben' ein."
      for t in $($FM get "$plans/$ref.md" aufgaben | tr ',' ' '); do
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
        st="$($FM get "$ep" status)"
        case "$st" in
          skizze)
            for sec in "## Zielbild des Themas" "## Vorhaben" "## Leitfragen" "## Done-Condition"; do
              grep -q "^$sec" "$ep" || block_stop "Epic-Abschnitt fehlt: $sec"
            done
            [ -n "$($FM get "$ep" vorhaben 2>/dev/null || true)" ] || block_stop "Epic: Frontmatter 'vorhaben' ist leer; trage die Plan-Namen der Vorhaben in Reihenfolge ein"
            ;;
          bewertet) block_stop "Epic-Abstimmung nicht abgeschlossen: setze status=aktiv (alle Leitentscheidungen als ADR) oder status=leitentscheidungen-offen (Vorlagen geschrieben)" ;;
          leitentscheidungen-offen)
            ls "$proj/.keel/decisions/pending/"*epic-"${ref#epic:}"* >/dev/null 2>&1 || block_stop "status leitentscheidungen-offen ohne Vorlage unter .keel/decisions/pending/*epic-${ref#epic:}*"
            ;;
          aktiv)
            [ -n "$($FM get "$ep" leitentscheidungen 2>/dev/null || true)" ] || block_stop "status aktiv verlangt Leitentscheidungen als ADR-Nummern im Frontmatter"
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
      st="$($FM get "$planfile" status)"
      case "$st" in
        entwurf)
          $FM validate "$planfile" --type plan --require vorhaben,titel,backlog,abstimmung 2>"$ERRF" \
            || block_stop "Plan unvollständig: $(cat "$ERRF")"
          for sec in "## Problemstellung" "## Pflichtkriterien" "## Akzeptanzkriterien"; do
            grep -q "^$sec" "$planfile" || block_stop "Plan-Abschnitt fehlt: $sec"
          done
          ;;
        problemstellung)
          [ "$($FM get "$planfile" abstimmung)" = "einig" ] || block_stop "status problemstellung verlangt abstimmung: einig"
          ;;
        blockiert)
          [ "$($FM get "$planfile" abstimmung)" = "vorlage" ] || block_stop "status blockiert verlangt abstimmung: vorlage"
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
        if grep -q "^## Klärung" "$t" && [ "$($FM get "$t" status 2>/dev/null)" = "neuschnitt" ]; then
          k="$($FM get "$t" klaerung 2>/dev/null || true)"
          [ "$k" = "beantwortet" ] || [ "$k" = "vorlage" ] || [ "$($FM get "$t" vorhaben)" != "$($FM get "$planfile" vorhaben)" ] \
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
        st="$($FM get "$ep" status)"
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
          n_pflege="$(grep -cE '^- .+ – .+ – wird Pflege' "$rep" || true)"
          [ "${n_pflege:-0}" -le "$max_pflege" ] || block_stop "Wochenrunde schlägt $n_pflege Pflegeaufgaben vor, erlaubt sind $max_pflege. Bündeln oder den Rest offen lassen."
        fi
        ;;
      *)
        planfile="$plans/$ref.md"
        st="$($FM get "$planfile" status)"
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
      [ "$($FM get "$done_f" entscheider)" = "Supervisor" ] || block_stop "Setze entscheider=Supervisor in der Vorlage"
      [ "$($FM get "$done_f" vorgelegt 2>/dev/null || true)" = "offen" ] || block_stop "Setze vorgelegt=offen, damit das Briefing die Entscheidung zeigt"
      grep -q "Warum nicht der Mensch" "$done_f" || block_stop "Abschnitt '## Entscheidung des Supervisors' mit 'Warum nicht der Mensch:' fehlt"
      grep -rlq "^vorlage: $vname" "$proj/.keel/adr/" 2>/dev/null || block_stop "Kein ADR mit 'vorlage: $vname' unter .keel/adr/ gefunden"
    elif [ -f "$pend_f" ]; then
      [ "$($FM get "$pend_f" eskaliert 2>/dev/null || true)" = "Supervisor" ] || block_stop "Vorlage weder entschieden (nach done/ verschoben) noch eskaliert (eskaliert=Supervisor, richtungsweisend=<Grund>)"
      $FM validate "$pend_f" --nonempty richtungsweisend,eskaliert_am 2>/dev/null || block_stop "Eskalation braucht richtungsweisend=<Grund> und eskaliert_am=<Datum>"
    else
      block_stop "Vorlage $vname weder unter pending/ noch unter done/"
    fi
    ;;
  compliance)
    rep="$proj/.keel/work/compliance/$ref.md"
    $FM validate "$rep" --type compliance --status frei,auflagen,vorlage --require aufgabe,datum 2>"$ERRF" \
      || block_stop "Compliance-Datei fehlt oder unvollständig ($rep): $(cat "$ERRF")"
    [ "$($FM get "$tasks/$ref.md" compliance 2>/dev/null || true)" = "$($FM get "$rep" status)" ] || block_stop "Setze compliance=<ergebnis> in der Aufgaben-Datei, gleich dem Status der Compliance-Datei"
    ;;
  coach)
    rep="$proj/.keel/work/coach/$ref.md"
    $FM validate "$rep" --type coachbericht --require datum,kennzahlen_verletzt,vorschlaege 2>"$ERRF" \
      || block_stop "Coach-Bericht fehlt oder unvollständig ($rep): $(cat "$ERRF")"
    # A model switch with enough runs for a comparison must be assessed (System-ADR 0015).
    need="$($CFG "$proj" faelligkeiten.coach_nach_modellwechsel_rollenlaeufe 10)"
    open_sw="$(python3 "$PLUGIN_ROOT/scripts/models.py" "$proj" --json 2>/dev/null | jq -r --argjson n "$need" '[.offene_wechsel[] | select(.laeufe >= $n) | .modell] | join(", ")' 2>/dev/null || true)"
    [ -z "$open_sw" ] || block_stop "Modellwechsel nicht bewertet: $open_sw. Vergleiche je Rolle altes und neues Modell (metrics.py, Tabelle 'Je Modell'), schreibe den Abschnitt '**Modellzuordnung:**' und setze modell_geprueft=[$open_sw] im Bericht."
    if [ -n "$($FM get "$rep" modell_geprueft 2>/dev/null || true)" ]; then
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
    status="$($FM get "$tasks/$ref.md" status)"
    if [ "$status" = "fertig-gemeldet" ]; then
      $FM validate "$tasks/$ref.md" --nonempty nachweis 2>/dev/null || block_stop "Feld 'nachweis' fehlt: trage die Testausgabe in Kurzform ein."
      out="$(bash "$PLUGIN_ROOT/scripts/gate.sh" "$proj" "$ref" 2>&1)" || block_stop "Prüftor rot. $out"
      excl=(':(exclude).keel')
      for t in $($FM get "$tasks/$ref.md" tests | tr ',' ' '); do excl+=(":(exclude)$t"); done
      diff_lines="$(cd "$proj" && git diff --numstat HEAD -- . "${excl[@]}" | awk '{s+=$1+$2} END {print s+0}')"
      max_diff="$($CFG "$proj" budget.diff_lines 300)"
      [ "$diff_lines" -le "$max_diff" ] || block_stop "Diff hat $diff_lines Zeilen, erlaubt sind $max_diff. Setze status: budget-erschoepft und beschreibe den Stand, der Planer schneidet neu."
      # Compliance scan: secrets block, new dependencies and personal data are recorded for the Lead
      rc=0; scan="$(python3 "$PLUGIN_ROOT/scripts/compliance_scan.py" "$proj" 2>&1)" || rc=$?
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
    runde="$($FM get "$tasks/$ref.md" review_runde)"
    rev="$proj/.keel/work/reviews/$ref-r$runde.md"
    $FM validate "$rev" --type review --status bestanden,befunde --require aufgabe,runde 2>"$ERRF" \
      || block_stop "Review-Datei fehlt oder unvollständig ($rev): $(cat "$ERRF")"
    # Threshold and trend are computed, not judged; the Lead reads review_ergebnis (System-ADR 0018)
    python3 "$PLUGIN_ROOT/scripts/review.py" pruefen "$proj" "$ref" >/dev/null 2>"$ERRF" \
      || block_stop "Review ungültig: $(cat "$ERRF")"
    [ "$($FM get "$rev" status)" = "bestanden" ] && python3 "$PLUGIN_ROOT/scripts/pflege.py" sammeln "$proj" "$rev" >/dev/null 2>&1 || true
    ;;
esac
finish "ok"
