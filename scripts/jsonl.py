#!/usr/bin/env python3
"""Append one JSON line to a log in the runtime folder of a project, atomically (keel.store.events).

Usage:
  jsonl.py append --project <dir>    read one JSON object from stdin, append it to events.jsonl
  jsonl.py hooklog --project <dir>   read a hook payload from stdin, keep what the learning loop and the monitor
                                     read, add ts, append it to hooks.jsonl; an unreadable payload becomes a
                                     hook_error line

Several hooks write the same files at the same time (parallel subagents, two hooks per event); every line is
one write under an exclusive lock (System-ADR 0019). Where the files lie comes from keel.store.paths.
Exit 0 on success, 2 on usage errors or a non-object input.
"""
import json
import sys

import _keel  # noqa: F401
from keel.store import events
from keel.store.paths import Paths

from keel.services.hooks.observe import trim  # noqa: E402  (one place for what the hook log keeps)


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("append", "hooklog") or sys.argv[2] != "--project":
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmd, paths = sys.argv[1], Paths(sys.argv[3])
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if cmd == "append":
        if not isinstance(data, dict):
            print("jsonl: input is not a JSON object", file=sys.stderr)
            sys.exit(2)
        events.append(paths.events, data)
        return
    if isinstance(data, dict):
        record = trim(data)
        record["ts"] = events.now_ts()
    else:
        record = {"hook_event_name": "hook_error", "ts": events.now_ts(), "detail": "payload is not a JSON object",
                  "bytes": len(raw)}
    events.append(paths.hooklog, record)


if __name__ == "__main__":
    main()
