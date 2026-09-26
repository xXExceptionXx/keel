#!/usr/bin/env bash
# SubagentStart: bind the parked task or plan reference to this agent id and reset its tool counter.
set -euo pipefail
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
role="$(keel_role "$(field '.agent_type')")"
[ -z "$role" ] && exit 0
id="$(field '.agent_id')"
sd="$(state_dir)"
ref=""
[ -f "$sd/pending-$role" ] && ref="$(cat "$sd/pending-$role")" && rm -f "$sd/pending-$role"
printf '%s\n' "$ref" > "$sd/agent-$id.ref"
printf '%s\n' "$role" > "$sd/agent-$id.role"
printf '0\n' > "$sd/agent-$id.calls"
date +%s > "$sd/agent-$id.start"
lead_model="$(transcript_model "$(field '.transcript_path')")"
record "agent_start" "$(jq -n --arg role "$role" --arg id "$id" --arg ref "$ref" --arg lead_model "$lead_model" '{role:$role,agent_id:$id,ref:$ref,lead_model:$lead_model}')"
exit 0
