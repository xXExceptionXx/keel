#!/usr/bin/env bash
# SubagentStart: bind the parked task or plan reference and the ADR state to this agent id, reset its tool counter.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_observer_init
agent_type="$(field '.agent_type')"
role="$(keel_role "$agent_type")"
[ -n "$role" ] || keel_ok
id="$(field '.agent_id')"
keel_paths
sd="$KEEL_PATH_STATE"
ref=""
[ -f "$sd/pending-$role" ] && ref="$(cat "$sd/pending-$role")" && rm -f "$sd/pending-$role"
[ -f "$sd/adrstand-$role.json" ] && mv -f "$sd/adrstand-$role.json" "$sd/agent-$id.adrstand.json"
printf '%s\n' "$ref" > "$sd/agent-$id.ref"
printf '%s\n' "$role" > "$sd/agent-$id.role"
printf '0\n' > "$sd/agent-$id.calls"
date +%s > "$sd/agent-$id.start"
lead_model="$(transcript_model "$(field '.transcript_path')")"
record "agent_start" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --arg lead_model "$lead_model" '{role:$role,agent_id:$id,ref:$ref,lead_model:$lead_model}')" || true
keel_ok
