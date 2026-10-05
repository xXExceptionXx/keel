#!/usr/bin/env bash
# PreToolUse on Agent: entry conditions of the keel roles (keel.services.hooks.agent_gate, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook pre-tool-use --only agent-gate
