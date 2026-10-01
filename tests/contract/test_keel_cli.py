"""bin/keel and flow.py from the outside (review of PR #13): the project cannot shadow the package, and files
that cannot be read are named instead of vanishing."""
import json
import subprocess
import unittest

from harness import BASH, REPO, ContractTest, project, write


class KeelCliTest(ContractTest):
    def test_a_keel_folder_in_the_project_does_not_shadow_the_package(self):
        p = project()
        write(p / "keel" / "__init__.py", "raise SystemExit('verdeckt')\n")
        proc = subprocess.run([BASH, str(REPO / "bin" / "keel"), "doctor", "--project", str(p), "--json"],
                              capture_output=True, text=True, env=self.env(), cwd=str(p))
        self.assertIn(proc.returncode, (0, 1), proc)
        self.assertIn("befunde", json.loads(proc.stdout))

    def test_flow_names_unreadable_files(self):
        p = project()
        write(p / ".keel" / "work" / "plans" / "kaputt.md", "---\ntyp: plan\nkein feld\n---\n")
        r = self.script("flow.py", "bereit", p, proj=p)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(r.json["unlesbar"], [".keel/work/plans/kaputt.md"])


if __name__ == "__main__":
    unittest.main()
