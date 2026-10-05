"""store.runtime: agent records, parked starts, session marks, the brake and activity markers (System-ADR 0022)."""
import json
import os
import subprocess
import sys
import time
import unittest

from tests.unit.base import TempTest
from keel.domain.errors import ReadError
from keel.store.paths import Paths
from keel.store.runtime import Runtime

COUNT = """
import sys
from keel.store.paths import Paths
from keel.store.runtime import Runtime
Runtime(Paths(sys.argv[1]).ensure()).count_call("a1")
"""


class RuntimeTest(TempTest):
    def setUp(self):
        super().setUp()
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        self.rt = Runtime(Paths(self.proj).ensure())

    def test_an_agent_lives_from_start_to_finish(self):
        self.rt.park_adr_snapshot("planer", {"adrs": {}})
        self.rt.start_agent("a1", "planer", "V1", start=100)
        self.assertEqual(self.rt.agent("a1"), {"id": "a1", "role": "planer", "ref": "V1", "start": 100, "calls": 0,
                                               "slow": False})
        self.assertEqual(self.rt.adr_snapshot("a1", "planer"), {"adrs": {}})
        self.assertEqual(self.rt.count_call("a1"), 1)
        self.assertTrue(self.rt.mark_slow("a1", 31))
        self.assertFalse(self.rt.mark_slow("a1", 32))
        self.assertEqual(self.rt.running_roles(), {"planer"})
        self.rt.finish_agent("a1", "planer")
        self.assertEqual(self.rt.agents(), [])
        self.assertIsNone(self.rt.adr_snapshot("a1", "planer"))

    def test_parallel_counts_are_not_lost(self):
        self.rt.start_agent("a1", "entwickler", "T1")
        env = {**self.env(), "KEEL_METRICS_DIR": os.environ["KEEL_METRICS_DIR"]}
        procs = [subprocess.Popen([sys.executable, "-c", COUNT, str(self.proj)], env=env) for _ in range(30)]
        for p in procs:
            self.assertEqual(p.wait(timeout=60), 0)
        self.assertEqual(self.rt.agent("a1")["calls"], 30)

    def test_a_broken_counter_is_a_read_error(self):
        self.rt.start_agent("a1", "entwickler", "T1")
        (self.rt.agents_dir / "a1.json").write_text('{"calls": "viele"}')
        with self.assertRaises(ReadError):
            self.rt.count_call("a1")
        (self.rt.agents_dir / "a1.json").write_text("kaputt")
        with self.assertRaises(ReadError):
            self.rt.count_call("a1")
        self.assertIsNone(self.rt.agent("a1")["calls"])

    def test_a_start_is_parked_once(self):
        self.assertTrue(self.rt.park("tester", "T1", "s1"))
        self.assertFalse(self.rt.park("tester", "T2", "s1"))
        ref, age = self.rt.pending("tester")
        self.assertEqual(ref, "T1")
        self.assertLess(age, 5)
        self.assertEqual([p["role"] for p in self.rt.pendings()], ["tester"])
        self.assertEqual(self.rt.take("tester"), "T1")
        self.assertIsNone(self.rt.pending("tester"))
        self.assertEqual(self.rt.take("tester"), "")

    def test_stop_failures_count_and_clear(self):
        self.rt.start_agent("a1", "tester", "T1")
        self.assertEqual([self.rt.stop_failure("a1") for _ in range(3)], [1, 2, 3])
        self.rt.clear_stop_failures("a1")
        self.assertEqual(self.rt.stop_failure("a1"), 1)

    def test_session_marks(self):
        self.assertFalse(self.rt.is_helper("s1"))
        self.rt.mark_helper("s1")
        self.rt.set_context_step("s1", 6)
        self.assertTrue(self.rt.is_helper("s1"))
        self.assertEqual(self.rt.context_step("s1"), 6)
        self.assertEqual(self.rt.context_step("s2"), 0)
        self.assertEqual(self.rt.briefing_path("s1").name, "s1.briefing.json")

    def test_brake(self):
        self.assertIsNone(self.rt.brake())
        self.rt.pull_brake("Notbremse seit heute\nzweite Zeile")
        self.assertEqual(self.rt.brake(), "Notbremse seit heute")

    def test_activity_markers(self):
        with self.rt.activity("prueftor", "T1"):
            [a] = self.rt.activities()
            self.assertEqual((a["name"], a["ref"], a["pid"], a["verwaist"]), ("prueftor", "T1", os.getpid(), False))
        self.assertEqual(self.rt.activities(), [])
        dead = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
        self.rt.activities_dir.mkdir(parents=True, exist_ok=True)
        (self.rt.activities_dir / "x.json").write_text(json.dumps({"name": "scan", "pid": int(dead.stdout),
                                                                   "start": int(time.time())}))
        self.assertTrue(self.rt.activities()[0]["verwaist"])

    def test_activity_marker_goes_on_an_exception(self):
        with self.assertRaises(RuntimeError):
            with self.rt.activity("scan"):
                raise RuntimeError("x")
        self.assertEqual(self.rt.activities(), [])


if __name__ == "__main__":
    unittest.main()
