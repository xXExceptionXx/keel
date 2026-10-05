"""Observers on every event: the hook log (raw data for the Coach and the monitor) and the Lead's context alarm.
Both never block (System-ADR 0019); a failure is recorded as hook_error by the dispatcher."""
from keel.services.hooks.base import Context
from keel.store import events, transcripts

HEAD = ("hook_event_name", "session_id", "agent_id", "agent_type", "tool_name", "tool_use_id", "cwd", "source",
        "transcript_path", "agent_transcript_path", "permission_mode", "stop_hook_active", "reason",
        "notification_type")
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
    if "message" in payload and payload.get("hook_event_name") == "Notification":
        out["message"] = cut(payload["message"], PROMPT_CHARS)
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        out["tool_input"] = {k: cut(tool_input[k], n) for k, n in TOOL_INPUT.items() if k in tool_input}
    if "duration_ms" in payload:
        out["duration_ms"] = payload["duration_ms"]
    return out


def log(hook):
    """Append the trimmed payload to hooks.jsonl, one write under a lock."""
    record = trim(hook.payload)
    record["ts"] = events.now_ts()
    events.append(hook.paths.hooklog, record)


def context_alarm(hook):
    """PostToolUse of the main session (the Lead): above the configured share of the window, tell the Lead to
    finish the task, write a handoff and stop. Once per 10-percent step. Subagents have budgets instead."""
    if hook.text("agent_type"):
        return None
    transcript = hook.text("transcript_path")
    if not transcript:
        return None
    window = int(hook.cfg("budget.context_window", "200000"))
    threshold = int(hook.cfg("budget.context_percent", "50"))
    _, used = transcripts.tail(transcript)
    if used <= 0:
        return None
    percent = used * 100 // window
    if percent < threshold:
        return None
    sid = hook.text("session_id")
    step = percent // 10
    if step <= hook.runtime.context_step(sid):
        return None
    msg = (f"keel Kontext-Alarm: Der Kontext dieser Session ist zu {percent} % gefüllt (Schwelle {threshold} %). "
           "Schließe die aktuelle Aufgabe sauber ab, schreibe eine Zwischenübergabe nach .keel/work/handoff/ und "
           "beende dich. Ein frischer Lead setzt aus der Übergabe fort.")
    try:
        hook.runtime.set_context_step(sid, step)
    except OSError:
        pass
    hook.try_record("context_alarm", {"session_id": sid, "used": used, "percent": percent})
    return Context(msg)
