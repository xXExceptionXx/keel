#!/usr/bin/env python3
"""Regression test for hooks/agent-gate.sh: every case from cases.py against the working tree and a git ref.

Usage: python3 tests/gate/run.py [--against REF] [--states "normal briefing tagesabschluss audit"] [--quick]

Builds the fixture project once per state (fixture.sh), sends each Agent tool call to the gate of both plugin
copies and compares the answer, the exit code, the parked reference (pending-<role>) and the recorded events.
Any difference is printed and fails the run. A change that is meant to alter the gate shows up here as the
exact list of calls whose outcome changed; check it is the intended one.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from cases import C  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def runtime_dir(root, proj, mdir):
    """Runtime folder of proj as this plugin copy lays it out: bin/keel since 0.15.0, the folder name before."""
    keel = Path(root) / "bin" / "keel"
    if not keel.exists():
        return mdir / proj.name
    out = subprocess.run(["bash", str(keel), "path", "runtime", "--project", str(proj)], capture_output=True, text=True,
                         check=True, env={**os.environ, "KEEL_METRICS_DIR": str(mdir)})
    return Path(out.stdout.strip())


def parked(sd):
    """Parked starts per role, whatever layout the plugin copy uses: pending-<role> files before 0.17.0,
    pending/<role>.json since (System-ADR 0022)."""
    out = {}
    if not sd.exists():
        return out
    for f in sorted(sd.glob("pending-*")):
        out[f.name[len("pending-"):]] = f.read_text().strip()
    for f in sorted(sd.glob("pending/*.json")):
        if not f.name.endswith(".adr.json"):
            out[f.stem] = json.loads(f.read_text()).get("ref", "")
    return out


def run(root, proj, mdir, t, p, bg):
    shutil.rmtree(mdir, ignore_errors=True)
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": str(proj), "session_id": "s1",
               "tool_input": {"subagent_type": t, "prompt": p, "run_in_background": bg}}
    r = subprocess.run(["bash", f"{root}/hooks/agent-gate.sh"], input=json.dumps(payload), capture_output=True,
                       text=True, env={**os.environ, "KEEL_METRICS_DIR": str(mdir)}, cwd=proj)
    rt = runtime_dir(root, proj, mdir)
    sd = rt / "state"
    pend = parked(sd)
    ev = rt / "events.jsonl"
    evs = [re.sub(r'"ts":"[^"]*",?', "", line) for line in ev.read_text().splitlines()] if ev.exists() else []
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr.strip(), "pending": pend, "events": evs}


def main():
    ref = arg("--against", "main")
    states = arg("--states", "normal briefing tagesabschluss audit").split()
    cases = C[::7] if "--quick" in sys.argv else C
    tmp = Path(tempfile.mkdtemp(prefix="keel-gate-"))
    try:
        old = tmp / "ref"
        old.mkdir()
        archive = subprocess.run(["git", "archive", ref], cwd=REPO, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(old)], input=archive, check=True)
        total = diffs = allowed = 0
        for state in states:
            proj = tmp / f"proj-{state}"
            subprocess.run(["bash", str(HERE / "fixture.sh"), str(proj), state], check=True)
            due = json.loads(subprocess.run([sys.executable, str(REPO / "scripts" / "due.py"), str(proj), "--json"],
                                            capture_output=True, text=True).stdout)
            print(f"[{state}] hart fällig: {[i['art'] for i in due['faellig'] if i['hart']] or 'nichts'}", flush=True)
            for t, p, bg in cases:
                a = run(old, proj, tmp / "m-ref", t, p, bg)
                b = run(REPO, proj, tmp / "m-new", t, p, bg)
                total += 1
                if a != b:
                    diffs += 1
                    print(f"ABWEICHUNG [{state}] {t} {p!r}\n  {ref}: {a}\n  jetzt: {b}")
                elif '"deny"' not in a["out"]:
                    allowed += 1
        print(f"{total} Fälle gegen {ref}, {diffs} Abweichungen ({allowed} erlaubt, {total - allowed - diffs} abgelehnt)")
        sys.exit(1 if diffs else 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
