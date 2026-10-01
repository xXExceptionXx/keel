"""keel doctor: reports each checked state of a project; exit 0 healthy, 1 findings, 2 cannot check."""
import json
import os
import subprocess
import time
import unittest

from harness import BASH, REPO, ContractTest, path_without, project, write


class DoctorTest(ContractTest):
    def doctor(self, p, path=None):
        proc = subprocess.run([BASH, str(REPO / "bin" / "keel"), "doctor", "--project", str(p), "--json"],
                              capture_output=True, text=True, env=self.env(path=path), cwd=str(p), timeout=60)
        data = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else None
        return proc, data

    def finding(self, p, check, path=None):
        proc, data = self.doctor(p, path)
        self.assertEqual(proc.returncode, 1, proc)
        found = {b["pruefung"]: b for b in data["befunde"] if b["stufe"] != "ok"}
        self.assertIn(check, found, data)
        return found[check]

    def test_healthy_project(self):
        proc, data = self.doctor(project())
        self.assertEqual(proc.returncode, 0, proc)
        self.assertTrue(all(b["stufe"] == "ok" for b in data["befunde"]), data)

    def test_config_with_a_wrong_value(self):
        p = project()
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as f:
            f.write("\nzusatz: 1\n")
        (p / ".keel" / "config.yaml").write_text(
            (p / ".keel" / "config.yaml").read_text(encoding="utf-8").replace("tool_calls: 60", "tool_calls: sechzig"),
            encoding="utf-8")
        self.assertIn("tool_calls", self.finding(p, "konfiguration")["meldung"])

    def test_config_that_cannot_be_read(self):
        p = project()
        write(p / ".keel" / "config.yaml", "budget:\n\ttool_calls: 60\n")
        self.assertEqual(self.finding(p, "konfiguration")["stufe"], "fehler")

    def test_emergency_brake(self):
        p = project()
        write(self.runtime(p) / "state" / "kern-gesperrt", "Notbremse seit gestern\n")
        self.assertEqual(self.finding(p, "notbremse")["stufe"], "fehler")

    def test_stale_pending_marker(self):
        p = project()
        f = self.runtime(p) / "state" / "pending-entwickler"
        write(f, "T-tb\n")
        old = time.time() - 3600
        os.utime(f, (old, old))
        self.finding(p, "pending")

    def test_broken_log_lines(self):
        p = project()
        write(self.runtime(p) / "events.jsonl", '{"event":"x","ts":"2026-10-01T00:00:00Z"}\nkaputt\n')
        self.assertIn("1", self.finding(p, "protokolle")["meldung"])

    def test_missing_jq(self):
        self.finding(project(), "jq", path=path_without("jq"))

    def test_missing_git(self):
        self.finding(project(), "git", path=path_without("git"))


if __name__ == "__main__":
    unittest.main()
