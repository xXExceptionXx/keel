#!/usr/bin/env bash
# PreToolUse on Skill and UserPromptSubmit: helper sessions, briefing model, monitor autostart
# (keel.services.hooks.skill_gate, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook --only skill-gate
