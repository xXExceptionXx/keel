"""Scripts that read the configuration end with exit 2 and a message when it cannot be read, never a traceback."""
import unittest

from harness import ContractTest, project, write


class ConfigErrorTest(ContractTest):
    def test_metrics_with_unreadable_config(self):
        p = project()
        write(p / ".keel" / "config.yaml", "budget:\n\ttool_calls: 60\n")
        r = self.script("metrics.py", p, "--json", proj=p)
        self.assertEqual(r.rc, 2, r)
        self.assertNotIn("Traceback", r.err)
        self.assertIn("config.yaml:2", r.err)

    def test_metrics_since_a_date(self):
        p = project()
        r = self.script("metrics.py", p, "--since", "2026-09-30", "--json", proj=p)
        self.assertIn(r.rc, (0, 3), r)
        self.assertEqual(r.json["seit"], "2026-09-30")


if __name__ == "__main__":
    unittest.main()
