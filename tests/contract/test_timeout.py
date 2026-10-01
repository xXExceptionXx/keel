"""Prüftor with a time limit: an internal limit shorter than the hook timeout, because a hook that times out lets
the call through (System-ADR 0019)."""
import json
import subprocess
import time
import unittest

from harness import REPO, ContractTest, project


def config_default(key):
    section, name = key.split(".")
    current = None
    for line in (REPO / "templates" / "keel" / "config.yaml").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(" ") and line.rstrip().endswith(":"):
            current = line.strip()[:-1]
        elif current == section and line.strip().startswith(name + ":"):
            return line.split(":", 1)[1].split("#")[0].strip()
    return None


class GateTimeoutTest(ContractTest):
    @unittest.expectedFailure
    def test_grandchildren_are_killed(self):
        cmd = 'bash -c \'(trap "" TERM; exec sleep 3713) & sleep 3712\''
        r = self.script("timeout.py", "1", "--", "bash", "-c", cmd, timeout=30)
        self.assertEqual(r.rc, 124, r)
        time.sleep(0.5)
        left = subprocess.run(["pgrep", "-f", "sleep 3713"], capture_output=True, text=True).stdout.split()
        for pid in left:
            subprocess.run(["kill", "-9", pid])
        self.assertEqual(left, [])

    @unittest.expectedFailure
    def test_limit_above_the_hook_timeout_is_capped(self):
        p = project()
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as f:
            f.write("\ntest:\n  command: true\n  timeout: 900\n")
        r = self.script("gate.sh", p, "probe", proj=p)
        self.assertEqual(r.rc, 0, r)
        self.assertIn("540", r.out)

    def test_developer_stop_is_refused_when_the_suite_runs_too_long(self):
        p = project()
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as f:
            f.write("\ntest:\n  command: sleep 30\n  timeout: 2\n")
        (p / ".keel" / "work" / "tasks" / "T-d.md").write_text(
            "---\ntyp: aufgabe\nid: T-d\nvorhaben: V9\ntitel: D\nstatus: fertig-gemeldet\nnachweis: grün\ntests: []\n---\n")
        sd = self.metrics / p.name / "state"
        sd.mkdir(parents=True)
        (sd / "agent-a1.ref").write_text("T-d\n")
        r = self.hook("agent-stop", {"hook_event_name": "SubagentStop", "agent_type": "keel:entwickler",
                                     "agent_id": "a1", "cwd": str(p), "last_assistant_message": "fertig"}, proj=p)
        self.assertEqual((r.json or {}).get("decision"), "block", r)
        self.assertIn("abgebrochen", r.json["reason"])

    def test_slow_test_suite_is_stopped(self):
        p = project()
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as f:
            f.write("\ntest:\n  command: sleep 30\n  timeout: 2\n")
        start = time.time()
        r = self.script("gate.sh", p, "probe", proj=p, timeout=60)
        self.assertLess(time.time() - start, 15)
        self.assertNotEqual(r.rc, 0, r)
        self.assertIn("abgebrochen", r.out)

    def test_hook_timeout_is_longer_than_the_test_limit(self):
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        stop = [h for entry in hooks["SubagentStop"] for h in entry["hooks"] if "agent-stop" in h["command"]][0]
        limit = config_default("test.timeout")
        self.assertIsNotNone(limit, "test.timeout fehlt im Template")
        self.assertGreater(stop.get("timeout", 0), int(limit) + 60)


if __name__ == "__main__":
    unittest.main()
