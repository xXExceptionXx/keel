#!/usr/bin/env bash
# PreToolUse on Bash: keel's own commands without a permission prompt (keel.services.hooks.allow, System-ADR 0025).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook pre-tool-use --only allow
