#!/usr/bin/env bash
# keel guard: second safety net behind the deny rules in .claude/settings.json.
# Deny rules match prefixes; this hook matches patterns anywhere in the command.
# Reads the PreToolUse payload from stdin and denies destructive Bash commands.
set -euo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("keel guard: " + $reason)
    }
  }'
  exit 0
}

# Git history and remote rewrites. Deleting a merged keel branch (vorhaben/*, reparatur/*) on the remote is allowed.
if printf '%s' "$cmd" | grep -Eq 'git[[:space:]]+push\b.*([[:space:]]-f\b|--force)'; then
  deny "force push is not allowed"
fi
if printf '%s' "$cmd" | grep -Eq 'git[[:space:]]+push\b.*([[:space:]]:[^[:space:]]|--delete)'; then
  cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty')"; [ -z "$cwd" ] && cwd="$(pwd)"
  cfg="$(dirname "${BASH_SOURCE[0]}")/../scripts/config.py"
  fp="$(python3 "$cfg" "$cwd" git.feature_prefix feature/)"; xp="$(python3 "$cfg" "$cwd" git.fix_prefix fix/)"
  esc() { printf '%s' "$1" | sed 's/[.[\*^$/]/\\&/g'; }
  # Judge every command segment on its own; a segment may end with a redirection.
  printf '%s\n' "$cmd" | sed -E 's/&&|\|\||;|\|/\n/g' | while IFS= read -r seg; do
    seg="$(printf '%s' "$seg" | sed -E 's/[[:space:]]+[0-9]*>&?[0-9]*[[:space:]]*[^[:space:]]*//g; s/^[[:space:]]+//; s/[[:space:]]+$//')"
    printf '%s' "$seg" | grep -Eq 'git[[:space:]]+push\b.*([[:space:]]:[^[:space:]]|--delete)' || continue
    printf '%s' "$seg" | grep -Eq "^git[[:space:]]+push[[:space:]]+[^[:space:]]+[[:space:]]+(--delete[[:space:]]+|:)($(esc "$fp")|$(esc "$xp"))[A-Za-z0-9._/-]+$" || echo DENY
  done | grep -q DENY && deny "deleting remote branches is only allowed for merged $fp* and $xp* branches"
fi

# File deletion outside the working directory
if printf '%s' "$cmd" | grep -Eq '(^|[[:space:];&|])rm[[:space:]]+-[a-zA-Z]*[rf]'; then
  if printf '%s' "$cmd" | grep -Eq 'rm[[:space:]]+-[a-zA-Z]*[rf][a-zA-Z]*[[:space:]]+([^[:space:]]*[[:space:]]+)*(/|~|\$HOME|\.\.)'; then
    deny "recursive delete on an absolute path, home or parent directory is not allowed"
  fi
fi

# Databases and infrastructure
if printf '%s' "$cmd" | grep -Eiq '\b(drop[[:space:]]+(database|table|schema)|truncate[[:space:]]+table)\b'; then
  deny "dropping or truncating database objects is not allowed"
fi
if printf '%s' "$cmd" | grep -Eq 'docker[[:space:]]+(system|volume|container|image)[[:space:]]+prune|mkfs\.|dd[[:space:]]+if=|:\(\)[[:space:]]*\{'; then
  deny "destructive system command is not allowed"
fi

# Remote code execution
if printf '%s' "$cmd" | grep -Eq '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh\b'; then
  deny "piping downloaded content into a shell is not allowed"
fi

exit 0
