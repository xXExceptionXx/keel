"""Every path of keel, computed in one place (N4, System-ADR 0020).

The runtime folder of a project lies outside the repository, below the metrics root
(KEEL_METRICS_DIR, default ~/.keel-metrics). Its name is the project key: folder name plus a short hash of
the resolved absolute path, so two projects named "app" share no events, markers or due items.
"""
import hashlib
import os
from pathlib import Path

ENV_ROOT = "KEEL_METRICS_DIR"
KEY_HASH_CHARS = 8


def metrics_root():
    return Path(os.environ.get(ENV_ROOT) or Path.home() / ".keel-metrics")


def project_key(project):
    p = Path(project).resolve()
    digest = hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:KEY_HASH_CHARS]
    return f"{p.name}-{digest}"


class Paths:
    """Paths of one project. Nothing is created until ensure()."""

    def __init__(self, project):
        self.project = Path(project).resolve()
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
