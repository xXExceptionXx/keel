#!/usr/bin/env bash
# keel-run: run a keel command unattended, ride out usage limits, and notify when a human is needed.
# Usage: keel-run.sh <project-dir> "<slash command>" [max-retries]
#   KEEL_NOTIFY_CMD   optional shell command that receives the message as $1 (default: macOS notification)
#   KEEL_RETRY_WAIT   seconds to wait after a usage limit before retrying (default 1800)
set -uo pipefail
project="$1"; cmd="$2"; retries="${3:-6}"
wait="${KEEL_RETRY_WAIT:-1800}"
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

notify() {
  if [ -n "${KEEL_NOTIFY_CMD:-}" ]; then
    bash -c "$KEEL_NOTIFY_CMD" _ "$1"
  elif command -v osascript >/dev/null; then
    osascript -e "display notification \"$1\" with title \"keel $(basename "$project")\"" 2>/dev/null || true
  fi
  echo "notify: $1"
}

cd "$project" || exit 2
if ! python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$project" >/dev/null; then
  notify "Briefing nötig, bevor der Lead arbeitet: /keel:briefing"
  exit 3
fi

attempt=0
while :; do
  attempt=$((attempt + 1))
  out="$(claude -p "$cmd" --permission-mode acceptEdits < /dev/null 2>&1)"; rc=$?
  printf '%s\n' "$out"
  if printf '%s' "$out" | grep -qiE "hit your (session|usage|weekly) limit|rate limit|resets"; then
    if [ "$attempt" -ge "$retries" ]; then notify "Limit erreicht, $attempt Versuche, aufgegeben: $cmd"; exit 4; fi
    echo "keel-run: usage limit, waiting ${wait}s (attempt $attempt/$retries)"
    sleep "$wait"
    continue
  fi
  break
done
if ! python3 "$PLUGIN_ROOT/scripts/briefing_needed.py" "$project" >/dev/null; then
  notify "Der Lead ist zu Ende; eine Entscheidung wartet auf dich: /keel:briefing"
fi
exit $rc
