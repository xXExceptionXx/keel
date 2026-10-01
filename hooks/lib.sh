#!/usr/bin/env bash
# Shared helpers for keel hooks. Source this file; expects $payload to hold the hook JSON.
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FM="python3 $PLUGIN_ROOT/scripts/frontmatter.py"
CFG="python3 $PLUGIN_ROOT/scripts/config.py"
KEEL_HOOK="$(basename "$0" .sh)"
KEEL_DONE=0
KEEL_ERR=""
KEEL_TMP=""
ERRF=/dev/null
KEEL_PATH_RUNTIME=""

# Error contract (System-ADR 0019). Claude Code blocks only on exit 2 or an explicit deny/block; any other
# failure lets the call through. A gate therefore ends through keel_ok, deny, block_stop or gate_fail; every
# other ending (errexit, unbound variable, missing tool) is caught by the EXIT trap and turned into exit 2.
# An observer never blocks: it records a hook_error event and ends with 0.

keel_ok() { KEEL_DONE=1; exit 0; }

gate_fail() {
  KEEL_DONE=1
  printf 'keel: %s konnte nicht prüfen (%s). Aus Sicherheitsgründen abgelehnt. /keel:hilfe erklärt den Stand.\n' "$KEEL_HOOK" "$1" >&2
  _keel_brake "$1"
  exit 2
}

_keel_gate_exit() {
  local rc=$?
  [ -n "$KEEL_TMP" ] && rm -rf "$KEEL_TMP"
  if [ "$KEEL_DONE" != 1 ]; then
    # Exit 2 here comes from gate_fail in a command substitution, which has already said why.
    if [ "$rc" -ne 2 ]; then
      printf 'keel: %s brach unerwartet ab (%s%s). Aus Sicherheitsgründen abgelehnt. /keel:hilfe erklärt den Stand.\n' \
        "$KEEL_HOOK" "$([ "$rc" -eq 0 ] && echo "Ursache unbekannt" || echo "Code $rc")" "${KEEL_ERR:+, $KEEL_ERR}" >&2
    fi
    _keel_brake "${KEEL_ERR:-Code $rc}"
    exit 2
  fi
}

# Emergency brake (System-ADR 0019). A SubagentStop that fails internally blocks the stop, but the role
# cannot repair the core and would retry forever. After the third internal failure of the same agent the
# stop goes through, keel is locked (state file kern-gesperrt) and agent-gate refuses every role until a
# human has fixed the cause and removed the lock. Applies only at the top level of agent-stop.sh.
_keel_brake() {
  [ "$KEEL_HOOK" = "agent-stop" ] && [ "${BASH_SUBSHELL:-0}" -eq 0 ] && [ -n "${sd:-}" ] && [ -n "${id:-}" ] || return 0
  local f="$sd/agent-$id.stopfail" n
  n="$(cat "$f" 2>/dev/null || echo 0)"
  is_number "$n" || n=0
  n=$((n + 1))
  printf '%s\n' "$n" > "$f" 2>/dev/null || return 0
  [ "$n" -ge 3 ] || return 0
  printf 'Notbremse seit %s: agent-stop konnte dreimal nicht prüfen (%s; Rolle %s, Bezug %s). Behebe die Ursache, dann lösche %s.\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "${role:-?}" "${ref:-?}" "$sd/kern-gesperrt" > "$sd/kern-gesperrt" 2>/dev/null || return 0
  hook_error "Notbremse: $1"
  rm -f "$f"
  KEEL_DONE=1
  printf 'keel: Notbremse gezogen, der Rollenlauf endet ungeprüft und alle Rollen sind gesperrt. Siehe %s.\n' "$sd/kern-gesperrt" >&2
  exit 0
}

# keel_gate_init [keel-only]: strict mode, fail-closed traps, tool and payload check, private temp dir.
# keel-only: without jq or python3, calls that do not concern keel pass instead of blocking every tool call.
keel_gate_init() {
  set -euo pipefail
  trap 'KEEL_ERR="Zeile $LINENO: $BASH_COMMAND"' ERR
  trap _keel_gate_exit EXIT
  if ! command -v jq >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    if [ "${1:-}" = keel-only ]; then
      case "$payload" in *keel:*) ;; *) keel_ok ;; esac
    fi
    gate_fail "jq und python3 werden gebraucht, mindestens eines fehlt im PATH"
  fi
  printf '%s' "$payload" | jq -e 'type == "object"' >/dev/null 2>&1 || gate_fail "Eingabe ist kein JSON-Objekt"
  KEEL_TMP="$(mktemp -d "${TMPDIR:-/tmp}/keel.XXXXXX")" || gate_fail "kein temporärer Ordner"
  ERRF="$KEEL_TMP/err"
}

_keel_observer_exit() {
  local rc=$?
  [ -n "$KEEL_TMP" ] && rm -rf "$KEEL_TMP"
  if [ "$KEEL_DONE" != 1 ]; then
    hook_error "Code $rc${KEEL_ERR:+, $KEEL_ERR}"
    exit 0
  fi
}

# keel_observer_init: strict mode, but every failure is recorded as hook_error and the call goes on.
keel_observer_init() {
  set -euo pipefail
  trap 'KEEL_ERR="Zeile $LINENO: $BASH_COMMAND"' ERR
  trap _keel_observer_exit EXIT
  if ! command -v jq >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    hook_error "jq oder python3 fehlt im PATH"
    keel_ok
  fi
  printf '%s' "$payload" | jq -e 'type == "object"' >/dev/null 2>&1 || { hook_error "Eingabe ist kein JSON-Objekt"; keel_ok; }
}

# hook_error <detail>: append a hook_error event without jq, best effort. Needs python3 for the path of the
# runtime folder (keel.store.paths); without python3 the error is lost, the hook still lets go.
hook_error() {
  local p; p="$(field '.cwd' 2>/dev/null || true)"
  [ -n "$p" ] || p="$PWD"
  local detail; detail="$(printf '%s' "$1" | tr '\n\t' '  ' | tr -d '\000-\037"\\' | cut -c1-300)"
  printf '{"event":"hook_error","ts":"%s","hook":"%s","detail":"%s"}' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$KEEL_HOOK" "$detail" \
    | python3 "$PLUGIN_ROOT/scripts/jsonl.py" append --project "$p" 2>/dev/null || true
}

is_number() { case "${1:-}" in ''|*[!0-9]*) return 1 ;; esac; }

# fm_get <file> <key>: the value, empty when the key or the frontmatter is missing; an unreadable file or a
# crash of frontmatter.py ends the gate (fail closed).
fm_get() {
  local rc=0 v
  v="$($FM get "$1" "$2" 2>"$ERRF")" || rc=$?
  case $rc in
    0) printf '%s' "$v" ;;
    1) ;;
    *) gate_fail "$1 nicht lesbar: $(cat "$ERRF" 2>/dev/null)" ;;
  esac
}

# fm_find <folder> key=value...: the first file whose frontmatter matches, empty when none; an unreadable file
# ends the gate (fail closed), because "none found" could be wrong.
fm_find() {
  local rc=0 v
  v="$($FM find "$@" 2>"$ERRF")" || rc=$?
  case $rc in
    0) printf '%s' "$v" | head -1 ;;
    1) ;;
    *) gate_fail "$1 nicht lesbar: $(cat "$ERRF" 2>/dev/null)" ;;
  esac
}

field() { printf '%s' "$payload" | jq -r "$1 // empty"; }

project_dir() {
  local cwd; cwd="$(field '.cwd')"
  [ -n "$cwd" ] && printf '%s' "$cwd" || pwd
}

# keel_paths: KEEL_PATH_ROOT, _RUNTIME, _STATE, _LOGS, _EVENTS, _HOOKLOG, _BRAKE for the project of this hook,
# from bin/keel (System-ADR 0020), once per hook process. Call it at the top level, not in $(...), so the
# values stay. Fails (return 1) when the path cannot be computed; errexit then ends the hook by its contract,
# but not inside an if, && or || list: there the caller checks it (keel_paths || gate_fail ...).
keel_paths() {
  [ -n "$KEEL_PATH_RUNTIME" ] && return 0
  local out; out="$("$PLUGIN_ROOT/bin/keel" path --project "$(project_dir)" --ensure --shell)" || return 1
  eval "$out"
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

# Model of the latest assistant turn in a transcript; empty when unknown. Reads the tail only and skips
# the partial first line and non-JSON lines, so large transcripts stay cheap.
transcript_model() {  # transcript_model <path>
  [ -f "$1" ] || return 0
  tail -c 400000 "$1" | jq -rR 'fromjson? | select(.type=="assistant") | .message.model // empty' 2>/dev/null \
    | grep -v '^<synthetic>$' | tail -1 || true
}

# Extract "Aufgabe: V1-T01" or "Vorhaben: rechnung" from a prompt.
prompt_field() { { printf '%s' "$1" | grep -oE "^$2:[[:space:]]*[A-Za-z0-9_.-]+" || true; } | head -1 | sed -E "s/^$2:[[:space:]]*//"; }

# deny and block_stop print the decision first and record it afterwards, so a failing record cannot turn a
# refusal into a pass. Should printing the decision itself fail, gate_fail blocks with exit 2.
deny() {
  jq -n --arg reason "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}' \
    || gate_fail "$1"
  record "denied" "$(jq -n --arg hook "$KEEL_HOOK" --arg role "${role:-}" --arg reason "$1" '{hook:$hook,role:$role,reason:$reason}')" || true
  keel_ok
}

block_stop() {
  jq -n --arg reason "$1" '{decision:"block",reason:$reason}' || gate_fail "$1"
  record "stop_blocked" "$(jq -n --arg role "${role:-}" --arg id "${id:-}" --arg ref "${ref:-}" --arg reason "$1" '{role:$role,agent_id:$id,ref:$ref,reason:$reason}')" || true
  keel_ok
}

record() {  # record <event> <json-fields>: append an event, atomically (scripts/jsonl.py)
  local line; line="$(jq -nc --arg ev "$1" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson f "$2" '{event:$ev,ts:$ts} + $f')" || return 0
  printf '%s' "$line" | python3 "$PLUGIN_ROOT/scripts/jsonl.py" append --project "$(project_dir)"
}
