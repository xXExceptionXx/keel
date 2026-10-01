"""Event logs (events.jsonl, hooks.jsonl): one place to append and to read (F8, F9).

Reading is tolerant: a line that is not UTF-8, not JSON, not an object, or has no usable `ts` is skipped and
counted, never a crash. Every event read carries `_ts`, an aware datetime in UTC.
Reading can start at a byte offset and reports where it stopped, so a caller can read incrementally later.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, NamedTuple, Optional

from keel.store.io import append_line


class ReadResult(NamedTuple):
    events: List[dict]
    end: int        # byte offset after the last complete line read
    skipped: int    # lines that could not be used


def parse_ts(value) -> Optional[datetime]:
    """Aware UTC datetime from an ISO text (`Z`, an offset, or naive which counts as UTC); None if unusable."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        t = datetime.fromisoformat(text)
    except ValueError:
        return None
    return t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dumps(record):
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


def append(path, record):
    """Append one event; sets ts when missing."""
    if "ts" not in record:
        record = {**record, "ts": now_ts()}
    append_line(path, dumps(record))


def read(path, since=None, start=0, tail_bytes=None) -> ReadResult:
    """Events of a JSON-lines file, oldest first.

    since: aware datetime; older events are left out (not counted as skipped).
    start: byte offset to begin at (from a previous ReadResult.end).
    tail_bytes: read at most this many bytes from the end; the partial first line is dropped.
    A last line without newline is not consumed: it may still be written.
    """
    path = Path(path)
    try:
        with path.open("rb") as f:
            size = f.seek(0, 2)
            begin = start
            partial_head = False
            if tail_bytes is not None and size - begin > tail_bytes:
                begin = size - tail_bytes
                partial_head = begin > 0
            f.seek(begin)
            data = f.read()
    except OSError:
        return ReadResult([], start, 0)
    lines = data.split(b"\n")
    rest = lines.pop()  # empty when the data ends with a newline
    end = begin + len(data) - len(rest)
    if partial_head and lines:
        lines.pop(0)
    events, skipped = [], 0
    for raw in lines:
        if not raw.strip():
            continue
        event = _parse_line(raw)
        if event is None:
            skipped += 1
            continue
        if since is not None and event["_ts"] < since:
            continue
        events.append(event)
    return ReadResult(events, end, skipped)


def _parse_line(raw):
    try:
        event = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(event, dict):
        return None
    ts = parse_ts(event.get("ts"))
    if ts is None:
        return None
    event["_ts"] = ts
    return event
