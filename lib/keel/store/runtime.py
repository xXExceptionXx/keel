"""Runtime state of a project under its runtime folder: running agents, parked starts, session marks, the
emergency brake and markers of long operations. Only this module knows how the state is laid out.

Agent:    role, ref (task or plan the run works on), start (epoch seconds), calls (tool calls so far),
          slow (minutes when the run passed its time budget), stopfail (internal failures at its end),
          ADR state at its start (System-ADR 0021).
Pending:  a role cleared by the agent gate, waiting for its SubagentStart to bind the ref to the agent id.
Session:  helper session (/keel:hilfe), briefing state for the end check, last context alarm step.
Brake:    text file kern-gesperrt; the human deletes it after fixing the cause (System-ADR 0019).
Activity: marker of a long operation (Prüftor, compliance scan) with process id; a marker whose process is gone
          is orphaned.

Counters change under a lock (N1), a pending start is created exclusively (N2).
"""
import contextlib
import json
import os
import time
from pathlib import Path

from keel.domain.errors import ReadError
from keel.store.io import atomic_write, create_exclusive, file_lock


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadError(f"{path}: nicht lesbar ({exc})") from exc


def _int(path, text):
    try:
        return int(text)
    except (TypeError, ValueError):
        raise ReadError(f"{path}: keine ganze Zahl: {text!r}")


def _remove(*paths):
    for p in paths:
        with contextlib.suppress(FileNotFoundError):
            Path(p).unlink()


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Runtime:
    """State of one project; paths is a keel.store.paths.Paths."""

    def __init__(self, paths):
        self.paths = paths
        self.state = paths.state

    # -- agents -------------------------------------------------------------------------------------------

    def _a(self, agent_id, suffix):
        return self.state / f"agent-{agent_id}.{suffix}"

    def start_agent(self, agent_id, role, ref):
        """Register a started role run: ref, role, zero calls, start time; the ADR state parked by the gate
        moves to the agent."""
        self.state.mkdir(parents=True, exist_ok=True)
        parked = self.state / f"adrstand-{role}.json"
        if parked.exists():
            os.replace(parked, self._a(agent_id, "adrstand.json"))
        atomic_write(self._a(agent_id, "ref"), f"{ref}\n")
        atomic_write(self._a(agent_id, "role"), f"{role}\n")
        atomic_write(self._a(agent_id, "calls"), "0\n")
        atomic_write(self._a(agent_id, "start"), f"{int(time.time())}\n")

    def agent(self, agent_id):
        """Known state of an agent: dict with role, ref, start, calls, slow. Values that are missing or cannot be
        read are '' (role, ref) or None (start, calls); the strict reads are count_call and its callers."""
        def read(suffix):
            try:
                return _read(self._a(agent_id, suffix))
            except ReadError:
                return None

        def number(suffix):
            try:
                return int(read(suffix))
            except (TypeError, ValueError):
                return None

        return {
            "id": agent_id,
            "role": read("role") or "",
            "ref": read("ref") or "",
            "start": number("start"),
            "calls": number("calls"),
            "slow": self._a(agent_id, "slow").exists(),
        }

    def count_call(self, agent_id):
        """One more tool call; returns the new count. A counter that cannot be read raises ReadError."""
        path = self._a(agent_id, "calls")
        with file_lock(path):
            text = _read(path)
            calls = _int(path, text) + 1 if text is not None else 1
            atomic_write(path, f"{calls}\n")
        return calls

    def mark_slow(self, agent_id, minutes):
        """Note that the run passed its time budget; True only the first time."""
        return create_exclusive(self._a(agent_id, "slow"), f"{minutes}\n")

    def stop_failure(self, agent_id):
        """One more internal failure at the end of this agent; returns the count."""
        path = self._a(agent_id, "stopfail")
        with file_lock(path):
            try:
                n = int(_read(path) or 0)
            except (ValueError, ReadError):
                n = 0
            n += 1
            atomic_write(path, f"{n}\n")
        return n

    def clear_stop_failures(self, agent_id):
        _remove(self._a(agent_id, "stopfail"))

    def adr_snapshot_path(self, agent_id, role):
        """File with the ADR state at the start of this run, or None."""
        for p in (self._a(agent_id, "adrstand.json"), self.state / f"adrstand-{role}.json"):
            if p.exists():
                return p
        return None

    def park_adr_snapshot_path(self, role):
        """Where the agent gate writes the ADR state before the role starts."""
        self.state.mkdir(parents=True, exist_ok=True)
        return self.state / f"adrstand-{role}.json"

    def finish_agent(self, agent_id, role):
        """Drop the state of a finished run."""
        _remove(*(self._a(agent_id, s) for s in ("ref", "role", "calls", "start", "slow", "stopfail",
                                                   "adrstand.json")),
                self.state / f"adrstand-{role}.json")

    def agents(self):
        """Ids of agents with state."""
        if not self.state.exists():
            return []
        return sorted({p.name.split(".")[0][len("agent-"):] for p in self.state.glob("agent-*.*")})

    def running_roles(self):
        """Roles of agents with state (started, no end yet)."""
        roles = set()
        for aid in self.agents():
            with contextlib.suppress(ReadError):
                role = _read(self._a(aid, "role"))
                if role:
                    roles.add(role)
        return roles

    # -- pending starts -------------------------------------------------------------------------------------

    def _p(self, role):
        return self.state / f"pending-{role}"

    def pending(self, role):
        """(ref, age in seconds) of a parked start of the role, or None."""
        path = self._p(role)
        try:
            age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            return None
        return (_read(path) or "", age)

    def park(self, role, ref, session=""):
        """Park the ref of a role that may start; False when a start of the role is parked already."""
        self.state.mkdir(parents=True, exist_ok=True)
        return create_exclusive(self._p(role), f"{ref}\n")

    def replace_pending(self, role, ref, session=""):
        """Replace an orphaned parked start."""
        atomic_write(self._p(role), f"{ref}\n")

    def take(self, role):
        """The parked ref of a role, removed; '' when none."""
        path = self._p(role)
        ref = _read(path)
        _remove(path)
        return ref or ""

    # -- sessions -------------------------------------------------------------------------------------------

    def mark_helper(self, session_id):
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / f"hilfe-{session_id}").touch()

    def is_helper(self, session_id):
        return bool(session_id) and (self.state / f"hilfe-{session_id}").exists()

    def briefing_path(self, session_id):
        """File with the state at the start of a briefing in this session (scripts/wiedervorlage.py)."""
        self.state.mkdir(parents=True, exist_ok=True)
        return self.state / f"briefing-{session_id}.json"

    def context_step(self, session_id):
        try:
            return int(_read(self.state / f"context-{session_id}.step") or 0)
        except (ValueError, ReadError):
            return 0

    def set_context_step(self, session_id, step):
        atomic_write(self.state / f"context-{session_id}.step", f"{step}\n")

    # -- emergency brake ------------------------------------------------------------------------------------

    def brake(self):
        """First line of the brake file, or None when keel is not locked."""
        text = _read(self.paths.brake)
        if text is None:
            return None
        return text.splitlines()[0] if text else ""

    def pull_brake(self, text):
        self.state.mkdir(parents=True, exist_ok=True)
        atomic_write(self.paths.brake, text.rstrip("\n") + "\n")

    # -- activities -----------------------------------------------------------------------------------------

    def _activities(self):
        return self.state / "activities"

    @contextlib.contextmanager
    def activity(self, name, ref=""):
        """Marker of a long operation while it runs; removed at the end, also on an exception."""
        folder = self._activities()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{name}-{os.getpid()}.json"
        atomic_write(path, json.dumps({"name": name, "ref": ref, "pid": os.getpid(), "start": int(time.time())}))
        try:
            yield
        finally:
            _remove(path)

    def activities(self):
        """Running and orphaned operations: dicts with name, ref, pid, start, verwaist."""
        out = []
        folder = self._activities()
        for p in sorted(folder.glob("*.json")) if folder.exists() else []:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                pid = int(data["pid"])
            except (OSError, ValueError, KeyError, TypeError):
                out.append({"name": p.stem, "ref": "", "pid": None, "start": None, "verwaist": True, "datei": str(p)})
                continue
            out.append({"name": data.get("name", p.stem), "ref": data.get("ref", ""), "pid": pid,
                        "start": data.get("start"), "verwaist": not _alive(pid), "datei": str(p)})
        return out
