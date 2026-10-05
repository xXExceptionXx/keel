"""Black-box harness for contract tests: payload or command line in, answer, exit code and events out.

The tests only talk to hooks and scripts through their public interface (stdin payload, argv, exit code,
stdout, files under the runtime folder), so they survive restructuring of the core. Where the runtime folder
of a project lies is asked from the plugin (`keel path`), never rebuilt here.

Environment:
  KEEL_TEST_BASH  bash to run the hooks with (CI and .githooks/pre-push set /bin/bash on macOS to cover bash 3.2)
"""
import atexit
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "gate" / "fixture.sh"
sys.path.insert(0, str(REPO / "lib"))
BASH = shutil.which(os.environ.get("KEEL_TEST_BASH", "bash")) or "bash"

_session = Path(tempfile.mkdtemp(prefix="keel-contract-"))
atexit.register(shutil.rmtree, _session, True)
_paths = {}
_fixtures = {}


def path_without(*tools):
    """A PATH value with every executable of the current PATH except the named tools (symlinks in a temp dir)."""
    key = tuple(sorted(tools))
    if key in _paths:
        return _paths[key]
    d = Path(tempfile.mkdtemp(prefix="path-", dir=_session))
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(entry)
        if not p.is_dir():
            continue
        for f in p.iterdir():
            if f.name in tools or os.path.lexists(d / f.name):
                continue
            try:
                if f.is_file() and os.access(f, os.X_OK):
                    (d / f.name).symlink_to(f)
            except OSError:
                continue
    _paths[key] = str(d)
    return _paths[key]


def project(state="normal"):
    """A fresh copy of the gate fixture project for the given state."""
    if state not in _fixtures:
        src = _session / f"fixture-{state}" / "proj"
        subprocess.run([BASH, str(FIXTURE), str(src), state], check=True, capture_output=True)
        _fixtures[state] = src
    dst = Path(tempfile.mkdtemp(prefix="proj-", dir=_session)) / "proj"
    shutil.copytree(_fixtures[state], dst, symlinks=True)
    return dst


def plugin_copy(overrides):
    """A copy of the plugin with files replaced: {relative path: new content}."""
    dst = Path(tempfile.mkdtemp(prefix="plugin-", dir=_session)) / "keel"
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(".git", "tests", "__pycache__"))
    for rel, content in overrides.items():
        f = dst / rel
        f.write_text(content, encoding="utf-8")
        f.chmod(0o755)
    return dst


_runtime = {}


def runtime_dir(metrics, proj):
    """Runtime folder of a project below the metrics root, as the plugin computes it (System-ADR 0020)."""
    key = (str(metrics), str(proj))
    if key not in _runtime:
        out = subprocess.run([BASH, str(REPO / "bin" / "keel"), "path", "runtime", "--project", str(proj)],
                             capture_output=True, text=True, check=True,
                             env={**os.environ, "KEEL_METRICS_DIR": str(metrics)})
        _runtime[key] = Path(out.stdout.strip())
    return _runtime[key]


CRASH_PY = "import sys\nraise RuntimeError('simulated crash')\n"


class Result:
    def __init__(self, proc, metrics, proj):
        self.rc = proc.returncode
        self.out = proc.stdout
        self.err = proc.stderr
        try:
            self.json = json.loads(proc.stdout) if proc.stdout.strip() else None
        except ValueError:
            self.json = None
        base = runtime_dir(metrics, proj) if proj else metrics
        self.events = _jsonl(base / "events.jsonl")
        self.hooklog = _jsonl(base / "hooks.jsonl")
        self.raw_hooklog = (base / "hooks.jsonl").read_text(encoding="utf-8") if (base / "hooks.jsonl").exists() else ""

    @property
    def blocked(self):
        if self.rc == 2:
            return True
        if self.rc != 0 or not isinstance(self.json, dict):
            return False
        hso = self.json.get("hookSpecificOutput") or {}
        return hso.get("permissionDecision") == "deny" or self.json.get("decision") == "block"

    def __repr__(self):
        return f"Result(rc={self.rc}, out={self.out[:400]!r}, err={self.err[:400]!r}, events={self.events[-3:]})"


def _jsonl(f):
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            out.append({"__invalid__": line})
    return out


class ContractTest(unittest.TestCase):
    """Base class: a private metrics folder and TMPDIR per test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="t-", dir=_session))
        self.metrics = self.tmp / "metrics"
        self.tmpdir = self.tmp / "tmp"
        self.tmpdir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def runtime(self, proj):
        """The runtime folder of proj under this test's metrics root."""
        return runtime_dir(self.metrics, proj)

    def env(self, extra=None, path=None):
        e = {**os.environ, "KEEL_METRICS_DIR": str(self.metrics), "TMPDIR": str(self.tmpdir)}
        if path is not None:
            e["PATH"] = path
        e.update(extra or {})
        return e

    def hook(self, name, payload, proj=None, root=REPO, env=None, path=None, timeout=120):
        """Run hooks/<name>.sh with the payload (dict or raw string) on stdin."""
        data = payload if isinstance(payload, str) else json.dumps(payload)
        proc = subprocess.run([BASH, str(Path(root) / "hooks" / f"{name}.sh")], input=data, capture_output=True,
                              text=True, env=self.env(env, path), cwd=str(proj or self.tmp), timeout=timeout)
        return Result(proc, self.metrics, proj)

    def script(self, name, *args, proj=None, root=REPO, env=None, path=None, timeout=120, stdin=None):
        """Run scripts/<name> (python or shell) with arguments."""
        f = Path(root) / "scripts" / name
        cmd = [sys.executable, str(f)] if f.suffix == ".py" else [BASH, str(f)]
        proc = subprocess.run(cmd + [str(a) for a in args], input=stdin, capture_output=True, text=True,
                              env=self.env(env, path), cwd=str(proj or self.tmp), timeout=timeout)
        return Result(proc, self.metrics, proj)

    @contextlib.contextmanager
    def _metrics_env(self):
        old = os.environ.get("KEEL_METRICS_DIR")
        os.environ["KEEL_METRICS_DIR"] = str(self.metrics)
        try:
            yield
        finally:
            if old is None:
                os.environ.pop("KEEL_METRICS_DIR", None)
            else:
                os.environ["KEEL_METRICS_DIR"] = old

    def state(self, proj, method, *args, **kwargs):
        """Call keel.store.runtime.Runtime.<method> for proj under this test's metrics root. The layout of the
        runtime state is the plugin's business (System-ADR 0022); tests read and seed it only through here."""
        from keel.store.paths import Paths
        from keel.store.runtime import Runtime
        with self._metrics_env():
            return getattr(Runtime(Paths(proj).ensure()), method)(*args, **kwargs)

    def seed_agent(self, proj, agent_id="a1", role="entwickler", ref="", start=None):
        """A running role as SubagentStart registers it."""
        self.state(proj, "start_agent", agent_id, role, ref, start=start)

    def age_state(self, proj, seconds):
        """Make every runtime state file of proj look `seconds` older (timestamps only, layout unknown)."""
        state = self.runtime(proj) / "state"
        for f in state.rglob("*") if state.exists() else []:
            st = f.stat()
            os.utime(f, (st.st_atime - seconds, st.st_mtime - seconds))

    def pending_of(self, proj, role):
        """(ref, age) of a parked start of the role, or None."""
        return self.state(proj, "pending", role)

    def agent_state(self, proj, agent_id="a1"):
        return self.state(proj, "agent", agent_id)

    def adr_snapshot(self, proj, agent_id="a1"):
        """The ADR state agent-gate notes at a role's start, bound to the agent as agent-start.sh does."""
        out = self.runtime(proj) / "state" / f"agent-{agent_id}.adrstand.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        r = self.script("adr.py", "stand", proj, out, proj=proj)
        self.assertEqual(r.rc, 0, r)
        return out

    def assertBlocked(self, r, msg=None):
        self.assertTrue(r.blocked, msg or f"expected a block, got {r!r}")

    def assertPassed(self, r, msg=None):
        self.assertEqual(r.rc, 0, msg or f"expected rc 0, got {r!r}")
        self.assertFalse(r.blocked, msg or f"expected no block, got {r!r}")


def agent_call(proj, subagent_type, prompt, session="s1", background=False):
    return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": str(proj), "session_id": session,
            "tool_input": {"subagent_type": subagent_type, "prompt": prompt, "run_in_background": background}}


def tool_call(proj, tool, tool_input, agent_type=None, agent_id=None, session="s1"):
    p = {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(proj), "session_id": session,
         "tool_input": tool_input}
    if agent_type:
        p["agent_type"] = agent_type
        p["agent_id"] = agent_id or "a1"
    return p


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
