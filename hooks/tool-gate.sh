#!/usr/bin/env bash
# PreToolUse inside a keel role: budgets, test and metrics protection (keel.services.hooks.tool_gate, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook pre-tool-use --only tool-gate
