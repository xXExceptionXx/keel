"""PreToolUse on Agent (gate): a keel role may only start when its input handoff exists and has the right status,
nothing hard is due that it does not satisfy, keel is not locked, and no start of the same role is pending.
Parks the task or plan reference so SubagentStart binds it to the agent id, and notes the ADR state for the end
check (System-ADR 0021).

A parked start that never reached SubagentStart (the human refused the call) is orphaned once no agent of the
role runs and it is older than ORPHAN_SECONDS; it is replaced instead of locking the role (N2). SubagentStart
does not carry the id of the Agent call, so this is decided by time and the running agents.

The entry rules per role are carried over unchanged from hooks/agent-gate.sh; M3 turns them into tables."""
import json
import re

from keel.domain import flow
from keel.services import adr
from keel.services.hooks import files, legacy
from keel.services.hooks.base import keel_role, prompt_field
from keel.store.io import atomic_write

STARTING_SECONDS = 600
ORPHAN_SECONDS = 30


class _Deny(Exception):
    def __init__(self, reason):
        self.reason = reason


def _deny(reason):
    raise _Deny(reason)


def S(key):
    return ",".join(flow.status(key))


def N(key):
    return flow.nonempty(key)


def run(hook):
    role = keel_role(hook.text("tool_input.subagent_type"))
    if not role:
        return None
    hook.role = role
    try:
        return _check(hook, role)
    except _Deny as d:
        return hook.deny(d.reason)


def _check(hook, role):
    type_ = hook.text("tool_input.subagent_type")
    # keel roles run sequentially and in the foreground: the Lead must see the result before it continues,
    # and the reference parking below relies on one start at a time.
    if hook.text("tool_input.run_in_background") == "true":
        _deny(f"keel-Rollen laufen im Vordergrund und nacheinander. Starte '{type_}' erneut mit run_in_background: false.")
    rt = hook.runtime
    # Emergency brake (System-ADR 0019): agent-stop could not check a handoff three times in a row.
    brake = rt.brake()
    if brake is not None:
        _deny(f"keel ist gesperrt (Notbremse): {brake}. /keel:hilfe erklärt den Stand.")
    # A helper session (/keel:hilfe) only observes; roles run in a fresh session.
    sid = hook.text("session_id")
    if rt.is_helper(sid):
        _deny("Diese Session ist eine Hilfe-Session (/keel:hilfe) und beobachtet nur. Rollen arbeiten in einer neuen "
              "Session mit /keel:start.")
    orphan = None
    pending = rt.pending(role)
    if pending is not None:
        ref, age = pending
        if age < STARTING_SECONDS and (role in rt.running_roles() or age <= ORPHAN_SECONDS):
            _deny(f"Rolle '{role}' wurde vor {int(age)} Sekunden bereits gestartet und läuft noch. keel arbeitet "
                  "sequenziell; warte auf ihr Ergebnis. Läuft nichts mehr: /keel:hilfe zeigt und räumt Reste auf.")
        orphan = (ref, int(age))

    _due(hook, role)
    ref = _entry(hook, role)

    proj = hook.project
    # ADR state at the start: agent-stop refuses an ADR written on a level not the role's own (System-ADR 0021)
    try:
        atomic_write(rt.park_adr_snapshot_path(role), json.dumps(adr.snapshot(proj), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        _deny(f"ADR-Stand nicht festhaltbar: {exc}. /keel:hilfe erklärt den Stand.")
    if orphan is not None:
        rt.replace_pending(role, ref, sid)
        hook.try_record("pending_verwaist", {"role": role, "ref": orphan[0], "alter": orphan[1]})
    elif not rt.park(role, ref, sid):
        _deny(f"Rolle '{role}' wurde gerade bereits gestartet und läuft noch. keel arbeitet sequenziell; warte auf "
              "ihr Ergebnis. Läuft nichts mehr: /keel:hilfe zeigt und räumt Reste auf.")
    return None


def _due(hook, role):
    """While something hard is due, only the roles that satisfy it may run. due.py exits 1 when something hard is
    due; anything but 0 or 1 means it could not tell, and then no role runs."""
    rc, out, err = legacy.run("due.py", hook.project, "--json")
    if rc not in (0, 1):
        last = err.rstrip("\n").splitlines()[-1] if err.strip() else ""
        _deny(f"Fälligkeiten nicht prüfbar (due.py endete mit {rc}: {last}). Keine Rolle startet, bis das behoben ist. "
              "/keel:hilfe erklärt den Stand.")
    try:
        due = json.loads(out)
        hart = due["hart"]
    except (ValueError, KeyError, TypeError):
        hart = None
    if hart not in (True, False):
        _deny("Fälligkeiten nicht prüfbar: due.py lieferte keine lesbare Antwort. /keel:hilfe erklärt den Stand.")
    if not hart:
        return
    items = [i for i in due.get("faellig", []) if i.get("hart")]
    allowed = set()
    for item in items:
        allowed.update(flow.DUE_ROLES.get(item.get("art"), []))
    if role not in allowed:
        what = "; ".join(f"{i.get('art')} ({i.get('grund')})" for i in items)
        _deny(f"Fällig, bevor Rollen arbeiten: {what}. Starte /keel:start, es arbeitet die Fälligkeiten in Reihenfolge "
              "ab. Unklar, was los ist: /keel:hilfe erklärt den Stand.")


def _require(problem, message):
    if problem:
        _deny(message.format(p=problem))


def _entry(hook, role):
    """Entry conditions of the role; returns the reference to park."""
    prompt = hook.text("tool_input.prompt")
    task = prompt_field(prompt, "Aufgabe")
    plan = prompt_field(prompt, "Vorhaben")
    proj = hook.project
    tasks = proj / ".keel" / "work" / "tasks"
    plans = proj / ".keel" / "work" / "plans"
    epics = proj / ".keel" / "work" / "epics"

    if role == "probe":
        pass
    elif role == "planer":
        if task:
            _require(files.check(tasks / f"{task}.md", typ="aufgabe", status=S("planer.neuschnitt")),
                     "Planer (Neuschnitt) darf nicht starten: {p}")
        else:
            if not plan:
                _deny("Planer braucht die Zeile 'Vorhaben: <name>' oder 'Aufgabe: <ID>' im Prompt")
            _require(files.check(plans / f"{plan}.md", typ="plan", status=S("planer.planung")),
                     "Planer darf nicht starten: {p}. Erst der Tester mit Abnahmetests.")
    elif role == "po":
        anlass = prompt_field(prompt, "Anlass")
        epic = prompt_field(prompt, "Epic")
        if anlass == "epic-skizze":
            if not (epic and prompt_field(prompt, "Backlog")):
                _deny("PO (epic-skizze) braucht 'Epic: <name>' und 'Backlog: <id>'")
            if (epics / f"{epic}.md").exists():
                _deny("PO (epic-skizze): Epic existiert schon")
            plan = f"epic:{epic}"
        elif anlass == "epic-abstimmung":
            if not epic:
                _deny("PO (epic-abstimmung) braucht 'Epic: <name>'")
            _require(files.check(epics / f"{epic}.md", typ="epic", status=S("po.epic-abstimmung")),
                     "PO (epic-abstimmung) darf nicht starten: {p}. Erst der Architekt mit Epic-Bewertung.")
            plan = f"epic:{epic}"
        elif anlass == "epic-abnahme":
            if not epic:
                _deny("PO (epic-abnahme) braucht 'Epic: <name>'")
            _require(files.check(epics / f"{epic}.md", typ="epic", status=S("po.epic-abnahme")),
                     "PO (epic-abnahme) darf nicht starten: {p}")
            plan = f"epic:{epic}"
        if not plan:
            _deny("PO braucht die Zeile 'Vorhaben: <name>' im Prompt")
        planfile = plans / f"{plan}.md"
        if anlass in ("epic-skizze", "epic-abstimmung", "epic-abnahme"):
            pass
        elif anlass == "problemstellung":
            if not prompt_field(prompt, "Backlog"):
                _deny("PO (problemstellung) braucht die Zeile 'Backlog: <id>'")
            if planfile.is_file():
                _require(files.check(planfile, typ="plan", status=S("po.problemstellung")),
                         "PO (problemstellung): Plan existiert schon: {p}")
        elif anlass == "abstimmung":
            _require(files.check(planfile, typ="plan", status=S("po.abstimmung"), nonempty=N("po.abstimmung")),
                     "PO (abstimmung) darf nicht starten: {p}. Erst der Architekt mit Bewertung.")
        elif anlass == "klaerung":
            if not task:
                _deny("PO (klaerung) braucht die Zeile 'Aufgabe: <ID>'")
            _require(files.check(tasks / f"{task}.md", typ="aufgabe", status=S("po.klaerung")),
                     "PO (klaerung) darf nicht starten: {p}")
            if not files.has_line(tasks / f"{task}.md", "## Klärung"):
                _deny("PO (klaerung): Aufgabe hat keinen Abschnitt '## Klärung'")
        elif anlass == "abnahme":
            _require(files.check(planfile, typ="plan", status=S("po.abnahme")), "PO (abnahme) darf nicht starten: {p}")
            if not (proj / ".keel" / "work" / "acceptance" / f"{plan}.md").is_file():
                _deny("PO (abnahme): Abnahmenachweis fehlt")
        else:
            _deny("PO braucht 'Anlass: problemstellung | abstimmung | klaerung | abnahme | epic-skizze | "
                  "epic-abstimmung | epic-abnahme'")
        task = plan
    elif role == "architekt":
        anlass = prompt_field(prompt, "Anlass")
        epic = prompt_field(prompt, "Epic")
        if anlass == "epic-bewertung":
            if not epic:
                _deny("Architekt (epic-bewertung) braucht 'Epic: <name>'")
            _require(files.check(epics / f"{epic}.md", typ="epic", status=S("architekt.epic-bewertung")),
                     "Architekt (epic-bewertung) darf nicht starten: {p}")
            task = f"epic:{epic}"
        elif anlass == "epic-retrospektive":
            if not (epic and plan):
                _deny("Architekt (epic-retrospektive) braucht 'Epic: <name>' und 'Vorhaben: <name>'")
            _require(files.check(epics / f"{epic}.md", typ="epic", status=S("architekt.epic-retrospektive")),
                     "Architekt (epic-retrospektive) darf nicht starten: {p}")
            _require(files.check(plans / f"{plan}.md", typ="plan", status=S("architekt.epic-retrospektive-vorhaben")),
                     "Architekt (epic-retrospektive): Vorhaben nicht integriert: {p}")
            task = f"epic:{epic}"
        elif anlass == "bewertung":
            if not plan:
                _deny("Architekt (bewertung) braucht 'Vorhaben: <name>'")
            _require(files.check(plans / f"{plan}.md", typ="plan", status=S("architekt.bewertung")),
                     "Architekt (bewertung) darf nicht starten: {p}")
            task = plan
        elif anlass == "strukturfrage":
            if not plan:
                _deny("Architekt (strukturfrage) braucht 'Vorhaben: <name>'")
            _require(files.check(plans / f"{plan}.md", typ="plan", status=S("architekt.strukturfrage")),
                     "Architekt (strukturfrage) darf nicht starten: {p}")
            task = plan
        elif anlass in ("bestandsaufnahme", "wochenrunde"):
            datum = prompt_field(prompt, "Datum")
            if not datum:
                _deny(f"Architekt ({anlass}) braucht 'Datum: YYYY-MM-DD'")
            task = f"{anlass}:{datum}"
        else:
            _deny("Architekt braucht 'Anlass: bewertung | strukturfrage | bestandsaufnahme | wochenrunde | "
                  "epic-bewertung | epic-retrospektive'")
    elif role == "compliance":
        if not task:
            _deny("Compliance braucht die Zeile 'Aufgabe: <ID>' im Prompt")
        if not (tasks / f"{task}.md").is_file():
            _deny(f"Compliance: Aufgabe {task} fehlt")
        if files.get(tasks / f"{task}.md", "compliance") != "pruefen":
            _deny("Compliance darf nicht starten: Aufgabe hat nicht compliance: pruefen")
        if not (proj / ".keel" / "work" / "compliance" / f"{task}.scan.md").is_file():
            _deny("Compliance: Scan-Datei fehlt")
    elif role == "supervisor":
        if prompt_field(prompt, "Anlass") != "entscheiden":
            _deny("Supervisor braucht 'Anlass: entscheiden'")
        m = re.search(r"^Vorlage:[ \t\r\f\v]*(\S+)", prompt, re.M)
        vfile = m.group(1) if m else ""
        if not vfile:
            _deny("Supervisor braucht 'Vorlage: <pfad>'")
        if not (proj / vfile).is_file():
            _deny(f"Supervisor: Vorlage {vfile} existiert nicht")
        _require(files.check(proj / vfile, typ="vorlage", status=S("supervisor.entscheiden")), "Supervisor: {p}")
        if files.get(proj / vfile, "eskaliert"):
            _deny("Supervisor: Vorlage ist bereits an den Menschen eskaliert")
        task = vfile
    elif role in ("auditor", "coach"):
        datum = prompt_field(prompt, "Datum")
        if not datum:
            _deny(f"{role} braucht die Zeile 'Datum: YYYY-MM-DD' im Prompt")
        task = datum
    elif role == "tester":
        if task:
            _require(files.check(tasks / f"{task}.md", typ="aufgabe", status=S("tester.aufgabe")),
                     "Tester darf nicht starten: {p}")
        elif plan:
            _require(files.check(plans / f"{plan}.md", typ="plan", status=S("tester.abnahmetests")),
                     "Tester darf nicht starten: {p}")
        else:
            _deny("Tester braucht 'Aufgabe: <ID>' oder 'Vorhaben: <name>' im Prompt")
    elif role == "entwickler":
        if not task:
            _deny("Entwickler braucht die Zeile 'Aufgabe: <ID>' im Prompt")
        tf = tasks / f"{task}.md"
        st = vh = ""
        if tf.is_file():
            st, vh = files.get(tf, "status"), files.get(tf, "vorhaben")
        if st == "reparatur" or vh == "R":
            # Repair tasks have no tests of their own; rework after a review is allowed (System-ADR 0018)
            _require(files.check(tf, typ="aufgabe", status=S("entwickler.reparatur")),
                     "Entwickler darf nicht starten: {p}")
        else:
            _require(files.check(tf, typ="aufgabe", status=S("entwickler.aufgabe"), nonempty=N("entwickler.aufgabe")),
                     "Entwickler darf nicht starten: {p}")
    elif role == "reviewer":
        if not task:
            _deny("Reviewer braucht die Zeile 'Aufgabe: <ID>' im Prompt")
        _require(files.check(tasks / f"{task}.md", typ="aufgabe", status=S("reviewer.aufgabe"),
                             nonempty=N("reviewer.aufgabe")),
                 "Reviewer darf nicht starten: {p}")
        # Snapshot of this round, so the next round can review the rework on its own (System-ADR 0018)
        rc, _, err = legacy.run("review.py", "stand", proj, task)
        if rc != 0:
            _deny(f"Reviewer: Stand der Runde nicht festgehalten: {legacy.strip(err)}")
    else:
        _deny(f"Unbekannte keel-Rolle '{role}'")
    return task or plan
