"""Runtime state of a project under its runtime folder (System-ADR 0022). Only this module knows the layout:

  state/agents/<id>.json        a running role: role, ref, start (epoch seconds), calls, slow (minutes when the run
                                passed its time budget), stopfail (internal failures at its end)
  state/agents/<id>.adr.json    ADR state at the run's start (System-ADR 0021)
  state/pending/<role>.json     a role cleared by the agent gate, waiting for SubagentStart: ref, session; the age
                                is the file's modification time
  state/pending/<role>.adr.json ADR state noted by the gate, moved to the agent at its start
  state/sessions/<sid>.json     helper session (/keel:hilfe), last context alarm step
  state/sessions/<sid>.briefing.json   state at the start of a briefing (scripts/wiedervorlage.py)
  state/activities/<name>-<pid>.json   a long operation (Prüftor, compliance scan) while it runs
  state/kern-gesperrt           the emergency brake, plain text; the human deletes it after fixing the cause
                                (System-ADR 0019)

Every change of a JSON record is a read-modify-write under a lock (N1); a pending start is created exclusively
(N2). Readers get dicts, never paths to parse.
"""
import contextlib
import json
import os
import time
from pathlib import Path

from keel.domain.errors import ReadError
from keel.store.io import atomic_write, create_exclusive, file_lock


def _load(path):
    """The JSON object in path, None when the file does not exist; ReadError when it cannot be read."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadError(f"{path}: nicht lesbar ({exc})") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ReadError(f"{path}: kein JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise ReadError(f"{path}: kein JSON-Objekt")
    return data


def _dump(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


def _remove(*paths):
    for p in paths:
        with contextlib.suppress(FileNotFoundError):
            Path(p).unlink()


def _age(path, now=None):
    try:
        return (now or time.time()) - Path(path).stat().st_mtime
    except FileNotFoundError:
        return None


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _int_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class Runtime:
    """State of one project; paths is a keel.store.paths.Paths."""

    def __init__(self, paths):
        self.paths = paths
        self.state = paths.state
        self.agents_dir = self.state / "agents"
        self.pending_dir = self.state / "pending"
        self.sessions_dir = self.state / "sessions"
        self.activities_dir = self.state / "activities"

    @contextlib.contextmanager
    def _update(self, path):
        """Read-modify-write of a JSON record under a lock: yields the dict, writes it back after the block."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with file_lock(path):
            data = _load(path) or {}
            yield data
            atomic_write(path, _dump(data))

    # -- agents -------------------------------------------------------------------------------------------

    def _agent(self, agent_id):
        return self.agents_dir / f"{agent_id}.json"

    def _agent_adr(self, agent_id):
        return self.agents_dir / f"{agent_id}.adr.json"

    def start_agent(self, agent_id, role, ref, start=None, calls=0):
        """Register a started role run: ref, role, zero calls, start time (now unless given); the ADR state parked
        by the gate moves to the agent."""
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        parked = self._pending_adr(role)
        if parked.exists():
            os.replace(parked, self._agent_adr(agent_id))
        atomic_write(self._agent(agent_id), _dump({"role": role, "ref": ref, "calls": calls,
                                                   "start": int(time.time() if start is None else start)}))

    def agent(self, agent_id):
        """Known state of an agent: dict with id, role, ref, start, calls, slow. Missing or unreadable values are
        '' (role, ref) or None (start, calls); the strict read is count_call."""
        try:
            data = _load(self._agent(agent_id)) or {}
        except ReadError:
            data = {}
        return {
            "id": agent_id,
            "role": str(data.get("role") or ""),
            "ref": str(data.get("ref") or ""),
            "start": _int_or_none(data.get("start")),
            "calls": _int_or_none(data.get("calls")),
            "slow": data.get("slow") is not None,
        }

    def count_call(self, agent_id):
        """One more tool call; returns the new count. A record or counter that cannot be read raises ReadError."""
        with self._update(self._agent(agent_id)) as data:
            calls = data.get("calls", 0)
            if isinstance(calls, bool) or not isinstance(calls, int):
                raise ReadError(f"{self._agent(agent_id)}: Zähler unlesbar: {calls!r}")
            data["calls"] = calls + 1
        return data["calls"]

    def mark_slow(self, agent_id, minutes):
        """Note that the run passed its time budget; True only the first time."""
        with self._update(self._agent(agent_id)) as data:
            first = data.get("slow") is None
            if first:
                data["slow"] = minutes
        return first

    def stop_failure(self, agent_id):
        """One more internal failure at the end of this agent; returns the count."""
        path = self._agent(agent_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(path):
            try:
                data = _load(path) or {}
            except ReadError:
                data = {}
            n = (_int_or_none(data.get("stopfail")) or 0) + 1
            data["stopfail"] = n
            atomic_write(path, _dump(data))
        return n

    def clear_stop_failures(self, agent_id):
        path = self._agent(agent_id)
        if not path.exists():
            return
        with contextlib.suppress(ReadError), self._update(path) as data:
            data.pop("stopfail", None)

    def adr_snapshot(self, agent_id, role):
        """ADR state at the start of this run (bound to the agent, else still parked for the role), or None.
        Raises ReadError when the file cannot be read."""
        for p in (self._agent_adr(agent_id), self._pending_adr(role)):
            data = _load(p)
            if data is not None:
                return data
        return None

    def park_adr_snapshot(self, role, snapshot):
        """The ADR state the agent gate notes before the role starts."""
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(self._pending_adr(role), json.dumps(snapshot, ensure_ascii=False))

    def bind_adr_snapshot(self, agent_id, snapshot):
        """The ADR state of a run, set directly (tests and tools; the hooks park it at the gate)."""
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(self._agent_adr(agent_id), json.dumps(snapshot, ensure_ascii=False))

    def finish_agent(self, agent_id, role):
        """Drop the state of a finished run."""
        _remove(self._agent(agent_id), self._agent_adr(agent_id), self._pending_adr(role))

    def agents(self):
        """State of every agent with a record, with its age in seconds and the files it holds (for cleanup)."""
        out = []
        if not self.agents_dir.exists():
            return out
        now = time.time()
        records = {p.stem for p in self.agents_dir.glob("*.json") if not p.name.endswith(".adr.json")}
        for aid in sorted(records):
            a = self.agent(aid)
            a["seit_sekunden"] = int(now - a["start"]) if a["start"] is not None else None
            a["dateien"] = [f for f in (self._agent(aid), self._agent_adr(aid)) if f.exists()]
            out.append(a)
        for p in sorted(self.agents_dir.glob("*.adr.json")):
            aid = p.name[:-len(".adr.json")]
            if aid not in records:
                out.append({"id": aid, "role": "", "ref": "", "start": None, "calls": None, "slow": False,
                            "seit_sekunden": None, "dateien": [p]})
        return out

    def running_roles(self):
        """Roles of agents with a record (started, no end yet)."""
        return {a["role"] for a in self.agents() if a["role"]}

    # -- pending starts -------------------------------------------------------------------------------------

    def _pending(self, role):
        return self.pending_dir / f"{role}.json"

    def _pending_adr(self, role):
        return self.pending_dir / f"{role}.adr.json"

    def pending(self, role):
        """(ref, age in seconds) of a parked start of the role, or None."""
        path = self._pending(role)
        age = _age(path)
        if age is None:
            return None
        try:
            data = _load(path) or {}
        except ReadError:
            data = {}
        return (str(data.get("ref") or ""), age)

    def pendings(self):
        """Every parked start: dicts with role, ref, seit_sekunden, datei."""
        out = []
        if not self.pending_dir.exists():
            return out
        for p in sorted(self.pending_dir.glob("*.json")):
            if p.name.endswith(".adr.json"):
                continue
            got = self.pending(p.stem)
            if got is not None:
                out.append({"role": p.stem, "ref": got[0], "seit_sekunden": int(got[1]), "datei": p})
        return out

    def parked_adr_files(self):
        """ADR states noted by the gate whose role never started, with their age in seconds, for cleanup."""
        if not self.pending_dir.exists():
            return []
        now = time.time()
        return [(p, _age(p, now)) for p in sorted(self.pending_dir.glob("*.adr.json"))]

    def park(self, role, ref, session=""):
        """Park the ref of a role that may start; False when a start of the role is parked already."""
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        return create_exclusive(self._pending(role), _dump({"ref": ref, "session": session}))

    def replace_pending(self, role, ref, session=""):
        """Replace an orphaned parked start."""
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(self._pending(role), _dump({"ref": ref, "session": session}))

    def take(self, role):
        """The parked ref of a role, removed; '' when none."""
        got = self.pending(role)
        _remove(self._pending(role))
        return got[0] if got else ""

    # -- sessions -------------------------------------------------------------------------------------------

    def _session(self, session_id):
        return self.sessions_dir / f"{session_id}.json"

    def session(self, session_id):
        try:
            return _load(self._session(session_id)) or {}
        except ReadError:
            return {}

    def mark_helper(self, session_id):
        with self._update(self._session(session_id)) as data:
            data["hilfe"] = True

    def is_helper(self, session_id):
        return bool(session_id) and self.session(session_id).get("hilfe") is True

    def briefing_path(self, session_id):
        """File with the state at the start of a briefing in this session (scripts/wiedervorlage.py writes and
        rewrites it)."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        return self.sessions_dir / f"{session_id}.briefing.json"

    def context_step(self, session_id):
        return _int_or_none(self.session(session_id).get("kontextstufe")) or 0

    def set_context_step(self, session_id, step):
        with self._update(self._session(session_id)) as data:
            data["kontextstufe"] = step

    def session_files(self):
        """Files of session marks with their age in seconds, for cleanup."""
        if not self.sessions_dir.exists():
            return []
        now = time.time()
        return [(p, _age(p, now)) for p in sorted(self.sessions_dir.glob("*.json"))]

    # -- emergency brake ------------------------------------------------------------------------------------

    def brake(self):
        """First line of the brake file, or None when keel is not locked."""
        try:
            text = self.paths.brake.read_text(encoding="utf-8", errors="replace").strip()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ReadError(f"{self.paths.brake}: nicht lesbar ({exc})") from exc
        return text.splitlines()[0] if text else ""

    def pull_brake(self, text):
        self.state.mkdir(parents=True, exist_ok=True)
        atomic_write(self.paths.brake, text.rstrip("\n") + "\n")

    # -- activities -----------------------------------------------------------------------------------------

    @contextlib.contextmanager
    def activity(self, name, ref=""):
        """Marker of a long operation while it runs; removed at the end, also on an exception."""
        self.activities_dir.mkdir(parents=True, exist_ok=True)
        path = self.activities_dir / f"{name}-{os.getpid()}.json"
        atomic_write(path, _dump({"name": name, "ref": ref, "pid": os.getpid(), "start": int(time.time())}))
        try:
            yield
        finally:
            _remove(path)

    def activities(self):
        """Running and orphaned operations: dicts with name, ref, pid, start, verwaist, datei."""
        out = []
        folder = self.activities_dir
        for p in sorted(folder.glob("*.json")) if folder.exists() else []:
            try:
                data = _load(p) or {}
                pid = int(data["pid"])
            except (ReadError, ValueError, KeyError, TypeError):
                out.append({"name": p.stem, "ref": "", "pid": None, "start": None, "verwaist": True, "datei": p})
                continue
            out.append({"name": data.get("name", p.stem), "ref": data.get("ref", ""), "pid": pid,
                        "start": data.get("start"), "verwaist": not _alive(pid), "datei": p})
        return out
