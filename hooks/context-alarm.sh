#!/usr/bin/env bash
# PostToolUse of the Lead: context alarm (keel.services.hooks.observe, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook post-tool-use --only context-alarm
