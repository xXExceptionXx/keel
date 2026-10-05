#!/usr/bin/env bash
# Hook log for the learning loop and the monitor (keel.services.hooks.observe, System-ADR 0022).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook --only log
