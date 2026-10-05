#!/usr/bin/env python3
"""Latency of the hooks per tool call, as Claude Code runs them: every command from hooks/hooks.json that
matches the event and tool, started in parallel, with the payload on stdin.

Usage: python3 tests/perf/hooks.py [--against REF] [--runs 20]

Scenarios: an Edit of a working role (PreToolUse and PostToolUse inside the subagent) and a Bash call of the
Lead (main session). Reported per scenario: the median wall time with the hooks in parallel (what the user
waits for) and the median sum of the single hook times (what the machine spends). With --against the same is
measured for a git ref (git archive), so before and after stand side by side. The agent is registered through
each copy's own SubagentStart hooks, so the comparison does not depend on the layout of the runtime folder.
"""
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "gate" / "fixture.sh"


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def commands(root, event, tool):
    """Commands of the hook entries in root/hooks/hooks.json that match the event and the tool name."""
    conf = json.loads((root / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    out = []
    for entry in conf.get("hooks", {}).get(event, []):
        matcher = entry.get("matcher", "")
        if matcher and tool is not None and not re.fullmatch(matcher, tool):
            continue
        out += [h["command"] for h in entry.get("hooks", []) if h.get("type") == "command"]
    return out


def start(root, cmd, payload, env):
    p = subprocess.Popen(["sh", "-c", cmd], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env={**env, "CLAUDE_PLUGIN_ROOT": str(root)},
                         cwd=payload["cwd"])
    p.stdin.write(json.dumps(payload).encode())
    p.stdin.close()
    return p


def parallel(root, event, payload, env):
    """Wall time with all matching hooks in parallel, and the sum of their single run times."""
    cmds = commands(root, event, payload.get("tool_name"))
    t0 = time.perf_counter()
    procs = [(start(root, c, payload, env), time.perf_counter()) for c in cmds]
    total = 0.0
    for p, began in procs:
        p.wait()
        total += time.perf_counter() - began
    return time.perf_counter() - t0, total


def scenario_payloads(proj, transcript):
    common = {"cwd": str(proj), "session_id": "perf", "transcript_path": str(transcript)}
    role = {**common, "agent_id": "perf1", "agent_type": "keel:entwickler"}
    edit = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "src" / "a.py"), "old_string": "a",
                                                "new_string": "b"}}
    bash = {"tool_name": "Bash", "tool_input": {"command": "git status --short"}}
    return {
        "Edit einer Rolle": [("PreToolUse", {**role, **edit, "hook_event_name": "PreToolUse"}),
                             ("PostToolUse", {**role, **edit, "hook_event_name": "PostToolUse",
                                              "tool_response": {"ok": True}})],
        "Bash des Leads": [("PreToolUse", {**common, **bash, "hook_event_name": "PreToolUse"}),
                           ("PostToolUse", {**common, **bash, "hook_event_name": "PostToolUse",
                                            "tool_response": {"stdout": ""}})],
    }


def measure(root, runs, tmp, label):
    proj = tmp / f"proj-{label}"
    subprocess.run(["bash", str(FIXTURE), str(proj), "normal"], check=True, capture_output=True)
    (proj / "src").mkdir(exist_ok=True)
    (proj / "src" / "a.py").write_text("a\n")
    transcript = tmp / f"transcript-{label}.jsonl"
    line = {"type": "assistant", "message": {"model": "claude-opus-5-5",
                                             "usage": {"input_tokens": 1000, "cache_read_input_tokens": 5000}}}
    transcript.write_text("\n".join(json.dumps(line) for _ in range(200)) + "\n")
    env = {**os.environ, "KEEL_METRICS_DIR": str(tmp / f"m-{label}")}
    # Register the role through the copy's own SubagentStart hooks.
    parallel(root, "SubagentStart", {"cwd": str(proj), "session_id": "perf", "transcript_path": str(transcript),
                                     "hook_event_name": "SubagentStart", "agent_id": "perf1",
                                     "agent_type": "keel:entwickler"}, env)
    result = {}
    for name, steps in scenario_payloads(proj, transcript).items():
        walls, sums = [], []
        for _ in range(runs):
            w = s = 0.0
            for event, payload in steps:
                a, b = parallel(root, event, payload, env)
                w += a
                s += b
            walls.append(w)
            sums.append(s)
        result[name] = (statistics.median(walls) * 1000, statistics.median(sums) * 1000)
    return result


def main():
    runs = int(arg("--runs", "20"))
    ref = arg("--against")
    tmp = Path(tempfile.mkdtemp(prefix="keel-perf-"))
    try:
        copies = [("Arbeitsstand", REPO)]
        if ref:
            old = tmp / "ref"
            old.mkdir()
            archive = subprocess.run(["git", "archive", ref], cwd=REPO, capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(old)], input=archive, check=True)
            copies.insert(0, (ref, old))
        print(f"Median aus {runs} Läufen, je Werkzeugaufruf PreToolUse und PostToolUse, in ms")
        print(f"{'Stand':<16} {'Szenario':<18} {'parallel':>9} {'Summe':>9}")
        for i, (label, root) in enumerate(copies):
            for name, (wall, total) in measure(root, runs, tmp, str(i)).items():
                print(f"{label:<16} {name:<18} {wall:>9.0f} {total:>9.0f}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
