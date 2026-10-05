#!/usr/bin/env bash
# SubagentStart: bind the parked reference to the agent (keel.services.hooks.agent_start, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook subagent-start --only agent-start
