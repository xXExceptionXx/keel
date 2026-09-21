#!/usr/bin/env bash
# keel log: append every hook payload as one JSON line to the metrics folder outside the repo.
# Raw data for the learning loop (Kennzahlen). Working roles never read this folder.
set -euo pipefail
payload="$(cat)"
project="$(printf '%s' "$payload" | jq -r '.cwd // empty')"
[ -z "$project" ] && project="$(pwd)"
dir="${KEEL_METRICS_DIR:-$HOME/.keel-metrics}/$(basename "$project")"
mkdir -p "$dir"
line="$(printf '%s' "$payload" | jq -c --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '. + {ts: $ts}')" || exit 0
printf '%s\n' "$line" >> "$dir/hooks.jsonl"
exit 0
