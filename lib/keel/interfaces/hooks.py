"""Hook dispatcher: `keel hook <event> [--only <step>]` (System-ADR 0022).

One process per Claude Code hook event. It reads the payload once, runs every step registered for the event
whose matcher fits, and answers in the format of the event. Steps run one after another; each runs even after
another one refused, so counters and logs stay as they were with parallel hooks. The first refusal wins,
additional context is joined.

Error contract (System-ADR 0019): a gate that cannot check (CannotCheck or any other exception) ends the call
with exit 2 and a message, so Claude Code blocks. At the end of a role (agent-stop) the third internal failure
of the same agent pulls the emergency brake instead: the stop goes through and every role is locked. An observer
never blocks: its failure is recorded as hook_error with the step name and the call goes on.

--only runs a single step (hooks/<step>.sh forward this way, so tests can address one step).
"""
import importlib
import json
import sys

GATE, OBSERVER = "gate", "observer"

EVENTS = {
    "pre-tool-use": "PreToolUse",
    "post-tool-use": "PostToolUse",
    "subagent-start": "SubagentStart",
    "subagent-stop": "SubagentStop",
    "stop": "Stop",
    "session-start": "SessionStart",
    "session-end": "SessionEnd",
    "notification": "Notification",
    "user-prompt-submit": "UserPromptSubmit",
}


def _tool(name):
    return lambda p: p.get("tool_name") == name


def _any(_payload):
    return True


# event -> steps in order: (name, kind, matcher, module in keel.services.hooks)
STEPS = {
    "PreToolUse": [
        ("guard", GATE, _tool("Bash"), "guard"),
        ("allow", OBSERVER, _tool("Bash"), "allow"),
        ("agent-gate", GATE, _tool("Agent"), "agent_gate"),
        ("skill-gate", GATE, _tool("Skill"), "skill_gate"),
        ("tool-gate", GATE, _any, "tool_gate"),
        ("log", OBSERVER, _any, "observe"),
    ],
    "PostToolUse": [("log", OBSERVER, _any, "observe"), ("context-alarm", OBSERVER, _any, "observe")],
    "SubagentStart": [("agent-start", OBSERVER, _any, "agent_start")],
    "SubagentStop": [("agent-stop", GATE, _any, "agent_stop")],
    "Stop": [("log", OBSERVER, _any, "observe"), ("briefing-stop", OBSERVER, _any, "briefing_stop")],
    "SessionStart": [("log", OBSERVER, _any, "observe"), ("session-gate", OBSERVER, _any, "session_gate")],
    "SessionEnd": [("log", OBSERVER, _any, "observe")],
    "Notification": [("log", OBSERVER, _any, "observe")],
    "UserPromptSubmit": [("log", OBSERVER, _any, "observe"), ("skill-gate", GATE, _any, "skill_gate")],
}

# Function of a step module when it is not run(): observe.py holds two steps.
FUNCTION = {"log": "log", "context-alarm": "context_alarm"}


def _say(text):
    sys.stderr.write(text.rstrip("\n") + "\n")


def _observer_error(hook, detail):
    from keel.store import events
    detail = " ".join(str(detail).split())
    detail = "".join(ch for ch in detail if ch >= " " and ch not in '"\\')[:300]
    try:
        events.append(hook.paths.events, {"event": "hook_error", "ts": events.now_ts(), "hook": hook.step,
                                          "detail": detail})
    except Exception:  # noqa: BLE001 - nothing left to report to
        pass


def _brake(hook, detail):
    """Third internal failure at the end of the same agent: let the stop through and lock every role.
    Returns True when the brake was pulled."""
    if hook.step != "agent-stop" or not hook.agent_id:
        return False
    from keel.store import events
    try:
        n = hook.runtime.stop_failure(hook.agent_id)
        if n < 3:
            return False
        brake = hook.paths.brake
        hook.runtime.pull_brake(
            f"Notbremse seit {events.now_ts()}: agent-stop konnte dreimal nicht prüfen ({detail}; Rolle "
            f"{hook.role or '?'}, Bezug {hook.ref or '?'}). Behebe die Ursache, dann lösche {brake}.")
        _observer_error(hook, f"Notbremse: {detail}")
        hook.runtime.clear_stop_failures(hook.agent_id)
    except Exception:  # noqa: BLE001 - without a brake the gate stays closed
        return False
    _say(f"keel: Notbremse gezogen, der Rollenlauf endet ungeprüft und alle Rollen sind gesperrt. Siehe {brake}.")
    return True


def _answer(event, refusal, contexts, allowed=None):
    if refusal is not None:
        if event == "PreToolUse":
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": refusal.reason}}
        return {"decision": "block", "reason": refusal.reason}
    if allowed is not None and event == "PreToolUse":
        out = {"hookEventName": "PreToolUse", "permissionDecision": "allow", "permissionDecisionReason": allowed.reason}
        if contexts:
            out["additionalContext"] = "\n\n".join(contexts)
        return {"hookSpecificOutput": out}
    if contexts:
        return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": "\n\n".join(contexts)}}
    return None


def run(event_arg, only=None, raw=None):
    """Run the hook steps; returns the exit code. Prints the answer to stdout, messages to stderr."""
    from keel.services.hooks.base import Allow, CannotCheck, Context, Hook, Refuse

    raw = sys.stdin.read() if raw is None else raw
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        payload = None

    event = EVENTS.get(event_arg) if event_arg else None
    if event_arg and event is None:
        _say(f"keel hook: unbekanntes Ereignis {event_arg!r}")
        return 2
    if event is None:
        named = (payload or {}).get("hook_event_name")
        homes = [e for e, steps in STEPS.items() if any(s[0] == only for s in steps)]
        event = named if named in homes else (homes[0] if homes else None)
    steps = [s for s in STEPS.get(event, []) if only is None or s[0] == only]
    if not steps:
        _say(f"keel hook: kein Schritt {only!r} für {event_arg or event}")
        return 2

    refusal, contexts, failed, allowed = None, [], None, None
    for name, kind, matcher, module in steps:
        hook = Hook(payload or {}, event, name)
        try:
            if payload is None:
                raise CannotCheck("Eingabe ist kein JSON-Objekt")
            if not matcher(payload):
                continue
            mod = importlib.import_module(f"keel.services.hooks.{module}")
            result = getattr(mod, FUNCTION.get(name, "run"))(hook)
        except Exception as exc:  # noqa: BLE001 - the error contract decides
            if kind == OBSERVER:
                _observer_error(hook, exc if isinstance(exc, CannotCheck) else f"{type(exc).__name__}: {exc}")
                continue
            if isinstance(exc, CannotCheck):
                detail, msg = str(exc), f"keel: {name} konnte nicht prüfen ({exc}). Aus Sicherheitsgründen abgelehnt."
            else:
                detail = f"{type(exc).__name__}: {exc}"
                msg = f"keel: {name} brach unerwartet ab ({detail}). Aus Sicherheitsgründen abgelehnt."
            if _brake(hook, detail):
                continue
            failed = failed or (msg + " /keel:hilfe erklärt den Stand.")
            continue
        if isinstance(result, Refuse) and refusal is None:
            refusal = result
        elif isinstance(result, Context):
            contexts.append(result.text)
        elif isinstance(result, Allow) and allowed is None:
            allowed = result
    if failed:
        _say(failed)
        return 2
    answer = _answer(event, refusal, contexts, allowed)
    if answer is not None:
        try:
            sys.stdout.write(json.dumps(answer, ensure_ascii=False, indent=2) + "\n")
            sys.stdout.flush()
        except OSError as exc:
            _say(f"keel: Antwort nicht ausgebbar ({exc}). Aus Sicherheitsgründen abgelehnt.")
            return 2
    return 0


def main(argv):
    """argv after 'hook': [<event>] [--only <step>]."""
    only = None
    args = list(argv)
    if "--only" in args:
        i = args.index("--only")
        if i + 1 >= len(args):
            _say("keel hook: --only braucht einen Schritt")
            return 2
        only = args[i + 1]
        del args[i:i + 2]
    if len(args) > 1 or (not args and only is None):
        _say("Aufruf: keel hook <ereignis> [--only <schritt>] | keel hook --only <schritt>")
        return 2
    try:
        return run(args[0] if args else None, only)
    except Exception as exc:  # noqa: BLE001 - a crash of the dispatcher itself blocks
        _say(f"keel: Hook-Dispatcher brach ab ({type(exc).__name__}: {exc}). Aus Sicherheitsgründen abgelehnt.")
        return 2
