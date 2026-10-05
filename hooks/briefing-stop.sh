#!/usr/bin/env bash
# Stop of the main session: briefing protocol check (keel.services.hooks.briefing_stop, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook stop --only briefing-stop
