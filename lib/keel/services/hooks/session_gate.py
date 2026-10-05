"""SessionStart (observer): tell the session up front when something is due, so the human hears it before working."""
from keel.services.hooks import legacy
from keel.services.hooks.base import Context


def run(hook):
    proj = hook.project
    if not (proj / ".keel" / "config.yaml").is_file():
        return None
    rc, out, _ = legacy.run("due.py", proj)
    out = legacy.strip(out)
    if rc == 0 and out == "nichts fällig":
        return None
    # exit 2, or exit 1 without output (a crash before due.py's own error handling), means it could not tell
    if rc >= 2 or rc < 0 or (rc == 1 and not out):
        msg = (f"keel: Fälligkeiten nicht prüfbar (interner Fehler in due.py, Code {rc}). keel-Rollen sind gesperrt, "
               "bis das behoben ist.")
    elif rc == 1:
        msg = ("keel: Fälligkeiten stehen aus, keel-Rollen sind bis dahin gesperrt. Starte /keel:start, es arbeitet "
               f"sie in Reihenfolge ab. {out}")
        if "briefing" in out:
            msg += (" Das Briefing braucht das Modell des Supervisors "
                    f"({hook.cfg('supervisor.model', 'claude-fable-5-1')}); stelle es vor /keel:start um.")
    else:
        msg = f"keel: Hinweise ohne Sperre. {out}"
    return Context(msg + " Für eine Erklärung des Stands: /keel:hilfe.")
