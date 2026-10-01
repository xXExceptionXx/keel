"""Every path of keel, computed in one place (N4, System-ADR 0020).

The runtime folder of a project lies outside the repository, below the metrics root
(KEEL_METRICS_DIR, default ~/.keel-metrics). Its name is the project key: folder name plus a short hash of
the resolved absolute path in its stored spelling, so two projects named "app" share no events, markers or due items.
"""
import hashlib
import os
from pathlib import Path

ENV_ROOT = "KEEL_METRICS_DIR"
KEY_HASH_CHARS = 8


def metrics_root():
    return Path(os.environ.get(ENV_ROOT) or Path.home() / ".keel-metrics")


_canonical = {}


def canonical(path):
    """The resolved path in the spelling the file system stores. On a case-insensitive file system (macOS)
    /users/x and /Users/x are the same folder; resolve() keeps whatever spelling it was given, the hooks get the
    stored one from Claude Code. Each part is looked up in its parent; a part that is not found as exactly one
    entry stays as it is."""
    p = Path(path).resolve()
    if p in _canonical:
        return _canonical[p]
    parts = [p.anchor]
    current = Path(p.anchor)
    for name in p.parts[1:]:
        try:
            entries = os.listdir(current)
        except OSError:
            entries = []
        if name not in entries:
            same = [e for e in entries if e.casefold() == name.casefold()]
            if len(same) == 1:
                name = same[0]
        parts.append(name)
        current = current / name
    result = Path(*parts)
    _canonical[p] = result
    return result


def project_key(project):
    p = canonical(project)
    digest = hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:KEY_HASH_CHARS]
    return f"{p.name}-{digest}"


class Paths:
    """Paths of one project. Nothing is created until ensure()."""

    def __init__(self, project):
        self.project = canonical(project)
        self.keel = self.project / ".keel"
        self.config = self.keel / "config.yaml"
        self.root = metrics_root()
        self.key = project_key(self.project)
        self.runtime = self.root / self.key
        self.state = self.runtime / "state"
        self.logs = self.runtime / "logs"
        self.events = self.runtime / "events.jsonl"
        self.hooklog = self.runtime / "hooks.jsonl"
        self.brake = self.state / "kern-gesperrt"
        self.monitor_pid = self.logs / "monitor.pid"
        self.monitor_log = self.logs / "monitor.log"

    def ensure(self):
        self.state.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        return self

    def by_name(self):
        """Name -> path for the command line (`keel path`)."""
        return {"root": self.root, "runtime": self.runtime, "state": self.state, "logs": self.logs,
                "events": self.events, "hooklog": self.hooklog, "brake": self.brake}


def lock_dir():
    """Lock files for files inside projects live here, so they never show up in a repository."""
    return metrics_root() / "locks"
