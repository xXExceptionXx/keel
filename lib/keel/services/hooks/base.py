"""What every hook step gets: the payload, the project, its runtime state and configuration, and the results a
step can give (refuse, add context). Error contract (System-ADR 0019): a gate that cannot check raises
CannotCheck or any other exception; the dispatcher then blocks. An observer's exception is recorded and the
call goes on."""
import json
import os
from pathlib import Path

from keel.domain.errors import KeelError
from keel.store import config, events
from keel.store.paths import Paths
from keel.store.runtime import Runtime


class CannotCheck(KeelError):
    """A gate could not decide; the dispatcher refuses for safety."""


class Refuse:
    """Deny the tool call or block the stop or prompt, with the reason shown to the model."""

    def __init__(self, reason):
        self.reason = reason


class Context:
    """Text added to the model's context (additionalContext)."""

    def __init__(self, text):
        self.text = text


def as_text(value):
    """A payload value as the hooks always read it (jq -r '. // empty'): null and false are empty."""
    if value is None or value is False:
        return ""
    if value is True:
        return "true"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


class Hook:
    def __init__(self, payload, event, step):
        self.payload = payload
        self.event = event
        self.step = step
        # Set by a step as soon as it knows them; the dispatcher uses them for the emergency brake.
        self.role = ""
        self.agent_id = ""
        self.ref = ""
        self._paths = None
        self._runtime = None
        self._config = None

    def get(self, dotted):
        node = self.payload
        for part in dotted.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return node

    def text(self, dotted):
        return as_text(self.get(dotted))

    @property
    def project(self):
        cwd = self.text("cwd")
        return Path(cwd) if cwd else Path(os.getcwd())

    @property
    def paths(self):
        if self._paths is None:
            self._paths = Paths(self.project).ensure()
        return self._paths

    @property
    def runtime(self):
        if self._runtime is None:
            self._runtime = Runtime(self.paths)
        return self._runtime

    @property
    def config(self):
        if self._config is None:
            self._config = config.load_file(Paths(self.project).config)
        return self._config

    def cfg(self, key, given=None):
        """A text value as scripts/config.py gives it: the file's value; else the given default; else the
        schema default. A list or section gives the default."""
        value = config.lookup(self.config, key)
        if value is None or value == "":
            value = given if given is not None else config.default(key)
        return value if isinstance(value, str) else (given or "")

    def cfg_int(self, key, given, what=None):
        value = self.cfg(key, str(given))
        try:
            return int(value)
        except ValueError:
            raise CannotCheck(f"{what or key} in .keel/config.yaml ist keine ganze Zahl: '{value}'")

    def role_limit(self, role, key, default):
        """budget.<role>_<key>, else budget.<key>, else the built-in default."""
        value = self.cfg(f"budget.{role}_{key}", "")
        if not value:
            value = self.cfg(f"budget.{key}", str(default))
        return value

    def record(self, event, fields):
        """Append an event to the project's events.jsonl."""
        events.append(self.paths.events, {"event": event, "ts": events.now_ts(), **fields})

    def try_record(self, event, fields):
        """Record, but never let a failing record change the decision."""
        try:
            self.record(event, fields)
        except Exception:  # noqa: BLE001 - the decision stands, the record is best effort
            pass

    def deny(self, reason, hook=None):
        """Refuse a tool call or prompt; recorded as denied."""
        self.try_record("denied", {"hook": hook or self.step, "role": self.role, "reason": reason})
        return Refuse(reason)

    def block_stop(self, reason):
        """Keep a role (or the session) going; recorded as stop_blocked."""
        self.try_record("stop_blocked", {"role": self.role, "agent_id": self.agent_id, "ref": self.ref,
                                         "reason": reason})
        return Refuse(reason)


def keel_role(agent_type):
    """'keel:planer' -> 'planer'; '' for agents that are not keel roles."""
    return agent_type[len("keel:"):] if isinstance(agent_type, str) and agent_type.startswith("keel:") else ""


def prompt_field(prompt, name):
    """Value of a line 'Name: value' (letters, digits, _.-) at a line start of the prompt, '' when missing."""
    import re
    m = re.search(rf"^{re.escape(name)}:[ \t\r\f\v]*([A-Za-z0-9_.-]+)", prompt or "", re.M)
    return m.group(1) if m else ""
