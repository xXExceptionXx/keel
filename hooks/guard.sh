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

# Git history and remote rewrites
if printf '%s' "$cmd" | grep -Eq 'git[[:space:]]+push\b.*([[:space:]]-f\b|--force|[[:space:]]:[^[:space:]]|--delete)'; then
  deny "force push, branch deletion on the remote or ref rewrite is not allowed"
fi
if printf '%s' "$cmd" | grep -Eq 'git[[:space:]]+(branch[[:space:]]+.*-D\b|reset[[:space:]]+--hard|filter-branch|reflog[[:space:]]+expire|gc[[:space:]]+--prune)'; then
  deny "destructive git operation is not allowed; use git stash or git restore"
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
