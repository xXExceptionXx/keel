"""Stop of the main session (observer that may block): when a briefing ran in it, its protocol must leave no open
point behind (System-ADR 0021). Checked only once a protocol was written since the briefing started; before that
the briefing is still a conversation. A finding blocks the stop with the reasons, at most three times; then the
check lets go and records briefing_protokoll_offen. An internal failure never traps the session."""
import json

from keel.services.hooks import legacy
from keel.services.hooks.base import Refuse
from keel.store import transcripts


def run(hook):
    proj = hook.project
    if not (proj / ".keel").is_dir():
        return None
    sid = hook.text("session_id")
    if not sid:
        return None
    marker = hook.runtime.briefing_path(sid)
    if not marker.exists():
        return None
    rc, out, err = legacy.run("wiedervorlage.py", "protokoll", proj, "--stand", marker)
    if rc > 1 or rc < 0:
        marker.unlink(missing_ok=True)
        last = err.rstrip("\n").splitlines()[-1] if err.strip() else f"Code {rc}"
        raise RuntimeError(f"Briefing-Protokoll nicht prüfbar: {last}")
    try:
        answer = json.loads(out)
        result = answer["ergebnis"]
    except (ValueError, KeyError, TypeError):
        marker.unlink(missing_ok=True)
        raise RuntimeError(f"unerwartete Antwort von wiedervorlage.py protokoll: {out}")
    if result == "offen":
        return None
    if result == "ok":
        marker.unlink(missing_ok=True)
        hook.try_record("briefing_geprueft", {"protokoll": answer.get("protokoll"), "session_id": hook.text("session_id"),
                                              "model": transcripts.last_model(hook.text("transcript_path"))})
        return None
    if result == "aufgegeben":
        marker.unlink(missing_ok=True)
        hook.try_record("briefing_protokoll_offen", {"protokoll": answer.get("protokoll"),
                                                     "gruende": answer.get("gruende"),
                                                     "session_id": hook.text("session_id"),
                                                     "model": transcripts.last_model(hook.text("transcript_path"))})
        return None
    if result == "fehler":
        reason = ("Das Briefing-Protokoll lässt offene Punkte zurück. Jeder offene Punkt wird eine Wiedervorlage "
                  "(wiedervorlage.py neu) und steht unter '## Zurückgestellt'; danach das Protokoll ergänzen und "
                  "committen: " + "; ".join(answer.get("gruende") or []))
        hook.try_record("stop_blocked", {"role": "supervisor", "agent_id": "", "ref": "briefing", "reason": reason})
        return Refuse(reason)
    marker.unlink(missing_ok=True)
    raise RuntimeError(f"unerwartete Antwort von wiedervorlage.py protokoll: {out}")
