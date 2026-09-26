#!/usr/bin/env bash
# Shared helpers for keel hooks. Source this file; expects $payload to hold the hook JSON.
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FM="python3 $PLUGIN_ROOT/scripts/frontmatter.py"
CFG="python3 $PLUGIN_ROOT/scripts/config.py"

field() { printf '%s' "$payload" | jq -r "$1 // empty"; }

project_dir() {
  local cwd; cwd="$(field '.cwd')"
  [ -n "$cwd" ] && printf '%s' "$cwd" || pwd
}

state_dir() {
  local p; p="$(project_dir)"
  local d="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}/$(basename "$p")/state"
  mkdir -p "$d"
  printf '%s' "$d"
}

log_dir() {
  local p; p="$(project_dir)"
  local d="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}/$(basename "$p")/logs"
  mkdir -p "$d"
  printf '%s' "$d"
}

# Role name without the plugin namespace: "keel:planer" -> "planer"; empty for non-keel agents.
keel_role() {
  local t="$1"
  case "$t" in
    keel:*) printf '%s' "${t#keel:}" ;;
    *) printf '' ;;
  esac
}

# Budget for a role: budget.<role>_<key> in .keel/config.yaml, else budget.<key>, else the built-in default.
role_limit() {  # role_limit <role> <key> <default>
  local p; p="$(project_dir)"
  local v; v="$($CFG "$p" "budget.$1_$2" "")"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  $CFG "$p" "budget.$2" "$3"
}

# Extract "Aufgabe: V1-T01" or "Vorhaben: rechnung" from a prompt.
prompt_field() { { printf '%s' "$1" | grep -oE "^$2:[[:space:]]*[A-Za-z0-9_.-]+" || true; } | head -1 | sed -E "s/^$2:[[:space:]]*//"; }

deny() {
  record "denied" "$(jq -n --arg hook "$(basename "$0" .sh)" --arg role "${role:-}" --arg reason "$1" '{hook:$hook,role:$role,reason:$reason}')"
  jq -n --arg reason "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
  exit 0
}

block_stop() {
  record "stop_blocked" "$(jq -n --arg role "${role:-}" --arg id "${id:-}" --arg ref "${ref:-}" --arg reason "$1" '{role:$role,agent_id:$id,ref:$ref,reason:$reason}')"
  jq -n --arg reason "$1" '{decision:"block",reason:$reason}'
  exit 0
}

record() {  # record <event> <json-fields>: append a metrics line
  local p; p="$(project_dir)"
  local d="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}/$(basename "$p")"
  mkdir -p "$d"
  local line; line="$(jq -nc --arg ev "$1" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson f "$2" '{event:$ev,ts:$ts} + $f')" || return 0
  printf '%s\n' "$line" >> "$d/events.jsonl"
}
