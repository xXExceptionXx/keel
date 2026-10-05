#!/usr/bin/env bash
# SubagentStop: exit rules of the roles, Prüftor, compliance scan (keel.services.hooks.agent_stop, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook subagent-stop --only agent-stop
