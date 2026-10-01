"""An artifact the codec refuses still blocks (System-ADR 0019), but every message names file and line, and
keel doctor finds it (review of PR #13)."""
import json
import subprocess
import unittest

from harness import BASH, REPO, ContractTest, agent_call, project, write

ADR = "---\nnummer: 0001\ntitel: Test\nKontext für Leser: x\n---\n# ADR\n"


class UnreadableArtifactTest(ContractTest):
    def broken_adr(self):
        p = project()
        write(p / ".keel" / "adr" / "0001-test.md", ADR)
        return p

    def test_due_names_file_and_line(self):
        p = self.broken_adr()
        r = self.script("due.py", p, "--json", proj=p)
        self.assertEqual(r.rc, 2, r)
        self.assertIn("0001-test.md:4", r.err)
        self.assertNotIn("Traceback", r.err)

    def test_role_start_is_denied_with_file_and_line(self):
        p = self.broken_adr()
        r = self.hook("agent-gate", agent_call(p, "keel:entwickler", "Aufgabe: T-tb"), proj=p)
        self.assertBlocked(r)
        self.assertIn("0001-test.md:4", r.out + r.err)

    def test_doctor_lists_the_file(self):
        p = self.broken_adr()
        proc = subprocess.run([BASH, str(REPO / "bin" / "keel"), "doctor", "--project", str(p), "--json"],
                              capture_output=True, text=True, env=self.env(), cwd=str(p))
        self.assertEqual(proc.returncode, 1, proc)
        found = {b["pruefung"]: b for b in json.loads(proc.stdout)["befunde"]}
        self.assertEqual(found["artefakte"]["stufe"], "fehler")
        self.assertIn("0001-test.md:4", found["artefakte"]["meldung"])

    def test_date_as_a_list_is_no_crash(self):
        p = project()
        write(p / ".keel" / "work" / "coach" / "2026-09-01-coach.md", "---\ntyp: coach\ndatum: [2026-09-01]\n---\n")
        r = self.script("due.py", p, "--json", proj=p)
        self.assertIn(r.rc, (0, 1), r)


if __name__ == "__main__":
    unittest.main()
