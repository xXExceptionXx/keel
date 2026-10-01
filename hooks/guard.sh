#!/usr/bin/env bash
# keel guard: second safety net behind the deny rules in .claude/settings.json.
# Deny rules match prefixes; this hook matches patterns anywhere in the command.
# Reads the PreToolUse payload from stdin and denies destructive Bash commands.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_gate_init
cmd="$(field '.tool_input.command')"
[ -n "$cmd" ] || keel_ok

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("keel guard: " + $reason)
    }
  }' || gate_fail "$1"
  record "denied" "$(jq -n --arg reason "$1" '{hook:"guard",role:"",reason:$reason}')" || true
  keel_ok
}

# Git history and remote rewrites. Deleting a merged keel branch (vorhaben/*, reparatur/*) on the remote is allowed.
if grep -Eq 'git[[:space:]]+push\b.*([[:space:]]-f\b|--force)' <<<"$cmd"; then
  deny "force push is not allowed"
fi
if grep -Eq 'git[[:space:]]+push\b.*([[:space:]]:[^[:space:]]|--delete)' <<<"$cmd"; then
  cwd="$(project_dir)"
  fp="$($CFG "$cwd" git.feature_prefix feature/)"; xp="$($CFG "$cwd" git.fix_prefix fix/)"
  esc() { printf '%s' "$1" | sed 's/[.[\*^$/]/\\&/g'; }
  # Judge every command segment on its own; a segment may end with a redirection. The verdict is collected
  # first: "| grep -q" would end early and turn the loop's SIGPIPE into a pass under pipefail. The loop
  # stops at the first offending segment, so after DENY a non-zero status (SIGPIPE upstream) is expected;
  # without DENY the pipeline must have succeeded, or the verdict is not trustworthy.
  vrc=0
  verdict="$(printf '%s\n' "$cmd" | sed -E 's/&&|\|\||;|\|/\n/g' | while IFS= read -r seg; do
    seg="$(printf '%s' "$seg" | sed -E 's/[[:space:]]+[0-9]*>&?[0-9]*[[:space:]]*[^[:space:]]*//g; s/^[[:space:]]+//; s/[[:space:]]+$//')"
    grep -Eq 'git[[:space:]]+push\b.*([[:space:]]:[^[:space:]]|--delete)' <<<"$seg" || continue
    grep -Eq "^git[[:space:]]+push[[:space:]]+[^[:space:]]+[[:space:]]+(--delete[[:space:]]+|:)($(esc "$fp")|$(esc "$xp"))[A-Za-z0-9._/-]+$" <<<"$seg" || { echo DENY; break; }
  done)" || vrc=$?
  case "$verdict" in *DENY*) deny "deleting remote branches is only allowed for merged $fp* and $xp* branches" ;; esac
  [ "$vrc" -eq 0 ] || gate_fail "Prüfung der Branch-Löschung fehlgeschlagen (Code $vrc)"
fi

# File deletion outside the working directory
if grep -Eq '(^|[[:space:];&|])rm[[:space:]]+-[a-zA-Z]*[rf]' <<<"$cmd"; then
  if grep -Eq 'rm[[:space:]]+-[a-zA-Z]*[rf][a-zA-Z]*[[:space:]]+([^[:space:]]*[[:space:]]+)*(/|~|\$HOME|\.\.)' <<<"$cmd"; then
    deny "recursive delete on an absolute path, home or parent directory is not allowed"
  fi
fi

# Databases and infrastructure
if grep -Eiq '\b(drop[[:space:]]+(database|table|schema)|truncate[[:space:]]+table)\b' <<<"$cmd"; then
  deny "dropping or truncating database objects is not allowed"
fi
if grep -Eq 'docker[[:space:]]+(system|volume|container|image)[[:space:]]+prune|mkfs\.|dd[[:space:]]+if=|:\(\)[[:space:]]*\{' <<<"$cmd"; then
  deny "destructive system command is not allowed"
fi

# Reading credentials: roles never need the values, scripts take them from the environment themselves
if grep -Eq '(^|[[:space:];&|])(env|printenv|export -p|set)([[:space:]]*$|[[:space:]]*\|)|gh[[:space:]]+auth[[:space:]]+token|\$\{?[A-Z_]*(TOKEN|SECRET|KEY|PASSWORD)[A-Z_]*\}?|(cat|less|head|tail|grep)[^|]*(\.env\b|\.netrc|id_rsa|credentials\.json|\.claude\.json)' <<<"$cmd"; then
  deny "reading credentials or the environment is not allowed; scripts read what they need themselves"
fi

# Remote code execution
if grep -Eq '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh\b' <<<"$cmd"; then
  deny "piping downloaded content into a shell is not allowed"
fi

keel_ok
