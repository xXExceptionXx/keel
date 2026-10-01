#!/usr/bin/env python3
"""Append one JSON line to a log file, atomically: one write on an O_APPEND file under an exclusive lock.

Usage:
  jsonl.py append <file>    read one JSON object from stdin, append it as one line
  jsonl.py hooklog <file>   read a hook payload from stdin, keep what the learning loop and the monitor read,
                            add ts, append it; an unreadable payload becomes a hook_error line

Several hooks write the same files at the same time (parallel subagents, two hooks per event). printf >> in
bash writes long lines in several chunks, which interleaved lines in real logs (System-ADR 0019).
Exit 0 on success, 2 on usage errors or a non-object input.
"""
import fcntl
import json
import os
import sys
from datetime import datetime, timezone

HEAD = ("hook_event_name", "session_id", "agent_id", "agent_type", "tool_name", "tool_use_id", "cwd", "source",
        "transcript_path", "agent_transcript_path", "permission_mode", "stop_hook_active")
TOOL_INPUT = {"skill": 200, "args": 200, "command": 2000, "subagent_type": 200, "description": 200, "file_path": 500,
              "prompt": 500, "run_in_background": None}
PROMPT_CHARS = 500


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append(path, record):
    line = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        view = memoryview(line)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


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
    if len(sys.argv) != 3 or sys.argv[1] not in ("append", "hooklog"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmd, path = sys.argv[1], sys.argv[2]
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if cmd == "append":
        if not isinstance(data, dict):
            print("jsonl: input is not a JSON object", file=sys.stderr)
            sys.exit(2)
        append(path, data)
        return
    if isinstance(data, dict):
        record = trim(data)
        record["ts"] = now()
    else:
        record = {"hook_event_name": "hook_error", "ts": now(), "detail": "payload is not a JSON object",
                  "bytes": len(raw)}
    append(path, record)


if __name__ == "__main__":
    main()
