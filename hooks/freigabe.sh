#!/usr/bin/env bash
# PermissionRequest: record a missing permission for the briefing (keel.services.hooks.freigabe, System-ADR 0025).
exec "$(dirname "${BASH_SOURCE[0]}")/../bin/keel" hook permission-request --only freigabe
