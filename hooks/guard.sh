#!/usr/bin/env bash
# PreToolUse on Bash: second safety net behind the deny rules (keel.services.hooks.guard, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook pre-tool-use --only guard
