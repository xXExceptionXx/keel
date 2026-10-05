"""PreToolUse on Skill and UserPromptSubmit (gate; a typed "/keel:<skill>" never passes the Skill tool), four duties:
1. /keel:hilfe marks the session as a helper session; the agent gate then refuses every role start in it.
2. The briefing is a conversation with the Supervisor and must run on the Supervisor's model. When /keel:briefing
   or /keel:start (with a briefing due) is invoked, the session's model is read from the transcript and the call
   is refused with instructions if it is not the configured one.
3. The start commands start the flow monitor when monitor.autostart is true (System-ADR 0017).
4. A briefing that may start leaves its starting state for the briefing end check (System-ADR 0021)."""
import json
import re

from keel.services.hooks import legacy
from keel.services.hooks.base import CannotCheck
from keel.store import transcripts

STARTS = {"start", "vorhaben", "epic", "tagesstart", "briefing"}


def _skill(hook):
    if hook.event == "UserPromptSubmit":
        m = re.search(r"^[ \t\r\f\v]*/keel:[a-z]+", hook.text("prompt"), re.M)
        return m.group(0).strip().lstrip("/") if m else ""
    return hook.text("tool_input.skill")


def _bare(skill):
    return skill[len("keel:"):] if skill.startswith("keel:") else skill


def run(hook):
    skill = _skill(hook)
    if not skill:
        return None
    name = _bare(skill)
    proj = hook.project
    if name in STARTS:
        try:
            legacy.run("monitor.py", proj, "--ensure", "--if-autostart", "--quiet", "--plugin-root",
                       legacy.PLUGIN_ROOT, timeout=20)
        except Exception:  # noqa: BLE001 - the monitor is a convenience, it never blocks a command
            pass
    if name == "hilfe":
        sid = hook.text("session_id")
        if sid:
            try:
                hook.runtime.mark_helper(sid)
            except OSError as exc:
                raise CannotCheck(f"Laufzeit-Ordner nicht bestimmbar ({exc})") from exc
        return None
    if name == "start":
        rc, out, err = legacy.run("briefing_needed.py", proj, "--json")
        # exit 1 counts only with a readable answer; a crash before the script's own error handling is exit 1 too
        if rc == 1:
            try:
                if json.loads(out).get("briefing_noetig") is not True:
                    rc = 2
            except (ValueError, AttributeError):
                rc = 2
        if rc == 0:
            return None
        if rc != 1:
            last = err.rstrip("\n").splitlines()[-1] if err.strip() else ""
            return hook.deny(f"Ob ein Briefing nötig ist, lässt sich nicht prüfen (briefing_needed.py endete mit {rc}: "
                             f"{last}). /keel:hilfe erklärt den Stand.")
    elif name != "briefing":
        return None
    required = hook.cfg("supervisor.model", "claude-fable-5-1")
    current = transcripts.last_model(hook.text("transcript_path"))
    if current and current != required:
        return hook.deny(
            f"Das Briefing läuft mit dem Supervisor und braucht dessen Modell ({required}); diese Session läuft auf "
            f"{current}. Stelle das Modell um (Modellwahl in der App oder /model {required}) und rufe {skill} erneut "
            f"auf. Alternativ aus dem Terminal: bash <plugin>/scripts/keel.sh {proj}. Unklar, was los ist: "
            "/keel:hilfe erklärt den Stand.")
    _note_briefing(hook)
    return None


def _note_briefing(hook):
    """The briefing may start: note its state, so the briefing end check can test the protocol (System-ADR 0021).
    Best effort: a missing marker only skips that check, it never stops the briefing."""
    sid = hook.text("session_id")
    if not sid:
        return
    try:
        marker = hook.runtime.briefing_path(sid)
        rc, out, err = legacy.run("wiedervorlage.py", "stand", hook.project)
        if rc == 0:
            marker.write_text(out, encoding="utf-8")
            return
        if marker.exists():
            marker.unlink()
        last = err.rstrip("\n").splitlines()[-1] if err.strip() else f"Code {rc}"
        hook.try_record("hook_error", {"hook": hook.step, "detail": f"Briefing-Stand nicht festgehalten: {last}"})
    except Exception as exc:  # noqa: BLE001
        hook.try_record("hook_error", {"hook": hook.step, "detail": f"Briefing-Stand nicht festgehalten: {exc}"})
