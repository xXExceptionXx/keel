#!/usr/bin/env bash
# SessionStart: due items up front (keel.services.hooks.session_gate, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook session-start --only session-gate
