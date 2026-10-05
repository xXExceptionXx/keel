"""PreToolUse for every tool inside a keel role (gate): tool-call budget, test protection, metrics folder protection,
a report when a run takes longer than its minutes (System-ADR 0021: time only reports), and file changes through
Bash refused with a pointer to Edit and Write (System-ADR 0027).

Paths are compared after normalising (U1, U3): `tests/./a.test.js`, `tests//a.test.js` and
`.keel/work/../../src/app.js` are what they point to. The metrics folder protection is a guard rail, not a
boundary (U2): it looks for the folder in the tool input, also as `~/.keel-metrics` or `$KEEL_METRICS_DIR`, but a
role determined to get there could spell it otherwise. Writes to test files through Bash are not caught here; the
test protection covers the file tools."""
import json
import os
import time

from keel.domain.errors import ReadError
from keel.services.hooks.base import CannotCheck, keel_role
from keel.services.hooks import files

FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def _real(path):
    return os.path.realpath(path)


def inside(target, folder):
    """Whether target (absolute, or relative to the folder's project) lies inside folder after normalising."""
    target, folder = _real(target), _real(folder)
    return target == folder or target.startswith(folder.rstrip(os.sep) + os.sep)


def relative(target, project):
    """target relative to project after normalising, or None when outside."""
    t, p = _real(os.path.join(project, target)), _real(project)
    if not inside(t, p):
        return None
    return os.path.relpath(t, p)


def metrics_spellings(root):
    """Ways the metrics folder can appear in a tool input."""
    root = str(root)
    out = {root, _real(root), "~/.keel-metrics", "$KEEL_METRICS_DIR", "${KEEL_METRICS_DIR}"}
    home = os.path.expanduser("~")
    for r in (root, _real(root)):
        if home and r.startswith(home + os.sep):
            rest = r[len(home):]
            out |= {"~" + rest, "$HOME" + rest, "${HOME}" + rest}
    return {s for s in out if s}


def run(hook):
    role = keel_role(hook.text("agent_type"))
    if not role:
        return None
    hook.role = role
    agent_id = hook.agent_id = hook.text("agent_id")
    tool = hook.text("tool_name")
    proj = str(hook.project)
    rt = hook.runtime
    state = rt.agent(agent_id)
    ref = hook.ref = state["ref"]

    # Metrics folder is off limits for working roles
    if role != "coach":
        tool_input = json.dumps(hook.get("tool_input"), ensure_ascii=False, separators=(",", ":"))
        if any(s in tool_input for s in metrics_spellings(hook.paths.root)):
            return hook.deny("Der Kennzahlen-Ordner ist für arbeitende Rollen gesperrt")

    # Roles change files with the file tools (System-ADR 0027): a Bash detour through a heredoc, tee, sed -i or an
    # inline script is not allowed in unattended runs anyway, and the role would only learn that from a silent denial.
    if tool == "Bash":
        from keel.services.hooks.allow import writes_files
        if writes_files(hook.text("tool_input.command")):
            return hook.deny("keel-Rollen ändern Dateien mit Edit oder Write, nicht über Bash (Heredoc, Umleitung in "
                             "eine Datei, tee, sed -i, python3 -/-c). Lies mit Read, ändere mit Edit, lege neu an mit "
                             "Write; Befehle wie Tests und git bleiben in Bash.")

    target = hook.text("tool_input.file_path") or hook.text("tool_input.notebook_path")

    # Developer must not touch the tester's files
    task = os.path.join(proj, ".keel", "work", "tasks", f"{ref}.md")
    if role == "entwickler" and ref and os.path.isfile(task) and tool in FILE_TOOLS and target:
        rel = relative(target, proj)
        for t in files.items(files.get(task, "tests")):
            if rel is not None and os.path.normpath(t) == rel:
                return hook.deny(f"Der Entwickler darf die Tests des Testers nicht ändern ({t}). Bei Widerspruch: "
                                 "Status testeinspruch setzen.")

    # Time budget: only reports (System-ADR 0021). Once per run a budget_slow event, never a refusal.
    minutes = hook.role_limit(role, "minutes", 30)
    if not minutes.isdigit():
        raise CannotCheck(f"Zeitbudget für {role} in .keel/config.yaml ist keine ganze Zahl: '{minutes}'")
    if state["start"] is not None and not state["slow"]:
        elapsed = int((time.time() - state["start"]) // 60)
        if elapsed >= int(minutes) and rt.mark_slow(agent_id, elapsed):
            hook.try_record("budget_slow", {"role": role, "agent_id": agent_id, "ref": ref, "minutes": elapsed,
                                            "limit": int(minutes)})

    # Tool-call budget, counted under a lock (N1)
    limit = hook.role_limit(role, "tool_calls", 60)
    if not limit.isdigit():
        raise CannotCheck(f"Werkzeugbudget für {role} in .keel/config.yaml ist keine ganze Zahl: '{limit}'")
    try:
        calls = rt.count_call(agent_id)
    except ReadError as exc:
        raise CannotCheck(f"Zähler in agent-{agent_id}.calls unlesbar: {exc}") from exc
    if calls > int(limit):
        if tool in ("Edit", "Write") and target:
            keel = os.path.join(proj, ".keel")
            if inside(os.path.join(proj, target), os.path.join(keel, "work")) or \
                    inside(os.path.join(proj, target), os.path.join(keel, "adr")):
                return None
        hook.try_record("budget_exhausted", {"role": role, "agent_id": agent_id, "ref": ref, "calls": calls})
        return hook.deny(f"Budget erschöpft ({limit} Werkzeugaufrufe). Schreibe deinen Stand in die Aufgaben-Datei "
                         "unter .keel/work/ und beende dich. Keine weiteren Werkzeuge.")
    return None
