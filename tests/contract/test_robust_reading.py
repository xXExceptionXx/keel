"""Tolerant reading (F8, F9): broken event lines, missing or offset timestamps and files that are not UTF-8
never crash a script; time is compared in UTC with time zone."""
import unittest

from harness import ContractTest, project, write

EVENTS = (b'{"event":"agent_stop","role":"tester","ts":"2026-09-30T10:00:00Z","model":"m1","agent_id":"a"}\n'
          b'kaputt\n'
          b'{"event":"agent_stop","role":"tester"}\n'
          b'{"event":"agent_stop","role":"tester","ts":"2026-09-30T12:00:00+02:00","model":"m1","agent_id":"b"}\n'
          b'["keine", "Abbildung"]\n'
          b'{"event":"agent_stop","ts":17}\n'
          b'{"event":"denied","ts":"2026-09-30T13:00:00Z","reason":"\xff\xfe"}\n'
          b'{"ts":"2026-09-30T14:00:00Z"}\n')


class RobustReadingTest(ContractTest):
    def broken_events(self):
        p = project()
        f = self.runtime(p) / "events.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(EVENTS)
        return p

    # Scripts run without proj=: the harness reads events.jsonl strictly as UTF-8, the scripts must not.
    def assertClean(self, r, codes=(0,)):
        self.assertIn(r.rc, codes, r)
        self.assertNotIn("Traceback", r.err)

    @unittest.expectedFailure
    def test_metrics_survives_broken_events(self):
        p = self.broken_events()
        self.assertClean(self.script("metrics.py", p, "--json"), (0, 3))

    @unittest.expectedFailure
    def test_models_survives_broken_events(self):
        p = self.broken_events()
        r = self.script("models.py", p, "--json")
        self.assertClean(r)
        self.assertEqual(r.json["aktuell_je_rolle"], {"tester": "m1"})

    @unittest.expectedFailure
    def test_lage_survives_broken_events(self):
        p = self.broken_events()
        self.assertClean(self.script("lage.py", p, "--json"))

    @unittest.expectedFailure
    def test_due_survives_broken_events(self):
        p = self.broken_events()
        self.assertClean(self.script("due.py", p, "--json"), (0, 1))

    @unittest.expectedFailure
    def test_since_with_offset(self):
        p = self.broken_events()
        self.assertClean(self.script("metrics.py", p, "--since", "2026-09-30T00:00:00+02:00", "--json"), (0, 3))

    @unittest.expectedFailure
    def test_metrics_survives_broken_values(self):
        p = project()
        write(p / ".keel" / "work" / "tasks" / "T-zwei.md", "---\ntyp: aufgabe\nid: T-zwei\nneuschnitt_runden: zwei\n---\n")
        write(p / ".keel" / "work" / "reviews" / "T-zwei-r1.md",
              "---\ntyp: review\naufgabe: T-zwei\nrunde: zwei\nstatus: befunde\n---\n")
        write(p / ".keel" / "decisions" / "done" / "v.md",
              "---\ntyp: vorlage\ndatum: gestern\nentschieden: heute\nstatus: entschieden\n---\n")
        self.assertClean(self.script("metrics.py", p, "--json"), (0, 3))

    @unittest.expectedFailure
    def test_lage_survives_a_file_that_is_not_utf8(self):
        p = project()
        (p / ".keel" / "work" / "plans" / "kaputt.md").write_bytes(b"---\ntyp: plan\ntitel: K\xe4se\n---\n")
        self.assertClean(self.script("lage.py", p, "--json"))


if __name__ == "__main__":
    unittest.main()
