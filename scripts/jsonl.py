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

HEAD = ("hook_event_name", "session_id", "agent_id", "agent_type", "tool_name", "tool_use_id", "cwd", "source",
        "transcript_path", "agent_transcript_path", "permission_mode", "stop_hook_active")
TOOL_INPUT = {"skill": 200, "args": 200, "command": 2000, "subagent_type": 200, "description": 200, "file_path": 500,
              "prompt": 500, "run_in_background": None}
PROMPT_CHARS = 500


def cut(value, limit):
    if limit is None or not isinstance(value, str):
        return value
    return value if len(value) <= limit else value[:limit - 1] + "…"


def trim(payload):
    """The parts of a hook payload that the monitor and the Coach read; no tool responses, no file contents."""
    out = {k: payload[k] for k in HEAD if k in payload}
    if "prompt" in payload:
        out["prompt"] = cut(payload["prompt"], PROMPT_CHARS)
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        out["tool_input"] = {k: cut(tool_input[k], n) for k, n in TOOL_INPUT.items() if k in tool_input}
    if "duration_ms" in payload:
        out["duration_ms"] = payload["duration_ms"]
    return out


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
