#!/usr/bin/env bash
# keel log: append every hook payload as one JSON line to the metrics folder outside the repo.
# Raw data for the learning loop (Kennzahlen) and the monitor. Working roles never read this folder.
# Only what those readers need is kept (no tool responses, no file contents), written atomically.
payload="$(cat)"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
keel_observer_init
printf '%s' "$payload" | python3 "$PLUGIN_ROOT/scripts/jsonl.py" hooklog --project "$(project_dir)"
keel_ok
