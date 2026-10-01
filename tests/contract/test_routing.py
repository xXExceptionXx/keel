"""Routing of audit findings (F6): an abort in the middle leaves no finding to be routed twice."""
import shutil
import unittest

from harness import ContractTest, project, write

REPORT = """---
typ: pruefbericht
datum: 2026-10-01
status: abweichungen
---
# Prüfbericht

- Erster Befund – src/a.py – wird Aufgabe
- Zweiter Befund – src/b.py – wird Vorlage
"""


class RoutingTest(ContractTest):
    def test_abort_after_the_first_finding_routes_nothing_twice(self):
        p = project()
        report = p / ".keel" / "work" / "audit" / "2026-10-01-pruefung.md"
        write(report, REPORT)
        pending = p / ".keel" / "decisions" / "pending"
        shutil.move(str(pending), str(p / "pending-weg"))
        pending.write_text("kein Ordner\n")  # writing the Vorlage fails
        first = self.script("route_findings.py", p, report, proj=p)
        self.assertNotEqual(first.rc, 0, first)
        self.assertRegex(report.read_text(encoding="utf-8"), r"wird Aufgabe → BL-\d+\n")

        pending.unlink()
        shutil.move(str(p / "pending-weg"), str(pending))
        second = self.script("route_findings.py", p, report, proj=p)
        self.assertEqual(second.rc, 0, second)
        backlog = (p / ".keel" / "backlog.md").read_text(encoding="utf-8")
        self.assertEqual(backlog.count("] Erster Befund\n"), 1, backlog)
        text = report.read_text(encoding="utf-8")
        self.assertRegex(text, r"wird Vorlage → \S+\.md\n")
        self.assertTrue(text.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
