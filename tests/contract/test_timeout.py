"""Prüftor with a time limit: an internal limit shorter than the hook timeout, because a hook that times out lets
the call through (System-ADR 0019)."""
import json
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
    def test_slow_test_suite_is_stopped(self):
        p = project()
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as f:
            f.write("\ntest:\n  command: sleep 30\n  timeout: 2\n")
        start = time.time()
        r = self.script("gate.sh", p, "probe", proj=p, timeout=60)
        self.assertLess(time.time() - start, 15)
        self.assertNotEqual(r.rc, 0, r)
        self.assertIn("abgebrochen", r.out)

    @unittest.expectedFailure
    def test_hook_timeout_is_longer_than_the_test_limit(self):
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        stop = [h for entry in hooks["SubagentStop"] for h in entry["hooks"] if "agent-stop" in h["command"]][0]
        limit = config_default("test.timeout")
        self.assertIsNotNone(limit, "test.timeout fehlt im Template")
        self.assertGreater(stop.get("timeout", 0), int(limit) + 60)


if __name__ == "__main__":
    unittest.main()
