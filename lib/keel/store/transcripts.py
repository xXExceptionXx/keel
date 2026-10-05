"""Reading Claude Code transcripts (JSON lines) from their end: model of the latest turn, context in use.

Only the last TAIL_BYTES are read; the partial first line and lines that are no JSON are skipped, so large
transcripts stay cheap and a line being written does not break the read.
"""
import json

TAIL_BYTES = 400000


def _assistant_turns(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            text = f.read().decode("utf-8", "replace")
    except OSError:
        return
    for line in text.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "assistant" and isinstance(rec.get("message"), dict):
            yield rec["message"]


def tail(path):
    """(model, tokens) of the latest assistant turns: the last model other than '<synthetic>' ('' if none) and
    the context in use by the last turn with usage (input plus cache read plus cache creation, 0 if none)."""
    model, used = "", 0
    for msg in _assistant_turns(path):
        m = msg.get("model") or ""
        if isinstance(m, str) and m and m != "<synthetic>":
            model = m
        usage = msg.get("usage")
        if isinstance(usage, dict):
            try:
                used = sum(int(usage.get(k) or 0) for k in
                           ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            except (TypeError, ValueError):
                pass
    return model, used


def last_model(path):
    return tail(path)[0] if path else ""
