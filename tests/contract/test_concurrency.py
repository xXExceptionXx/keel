"""Shared files under parallel writers (N6): no lost entries, no duplicate IDs."""
import re
import subprocess
import sys
import unittest

from harness import REPO, ContractTest, project, write

REVIEW = """---
typ: review
aufgabe: T-{n}
runde: 1
status: bestanden
---
| Schweregrad | Herkunft | Fundstelle | Beschreibung |
| --- | --- | --- | --- |
| anmerkung | neu | src/x{n}.py | Anmerkung {n} |
"""


class ConcurrencyTest(ContractTest):
    def parallel(self, cmds, p):
        procs = [subprocess.Popen(c, cwd=str(p), env=self.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for c in cmds]
        for proc in procs:
            _, err = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0, err)

    def test_parallel_pflege_sammeln_gives_unique_ids(self):
        p = project()
        n = 50
        reviews = []
        for i in range(n):
            f = p / ".keel" / "work" / "reviews" / f"T-{i}-r1.md"
            write(f, REVIEW.format(n=i))
            reviews.append(f)
        self.parallel([[sys.executable, str(REPO / "scripts" / "pflege.py"), "sammeln", str(p), str(f)] for f in reviews], p)
        ids = re.findall(r"^\| (P-\d+) \|", (p / ".keel" / "work" / "pflege.md").read_text(encoding="utf-8"), re.M)
        self.assertEqual(len(ids), n)
        self.assertEqual(len(set(ids)), n)

    def test_parallel_backlog_propose_gives_unique_ids(self):
        p = project()
        n = 40
        files = []
        for i in range(n):
            f = p / f"neu-{i}.md"
            write(f, f"---\ntitel: Neu {i}\nproblem: p\nwarum: w\nherkunft: Audit\n---\n")
            files.append(f)
        self.parallel([[sys.executable, str(REPO / "scripts" / "backlog.py"), "--project", str(p), "propose", str(f)]
                       for f in files], p)
        ids = re.findall(r"^- \[(BL-\d+)\]", (p / ".keel" / "backlog.md").read_text(encoding="utf-8"), re.M)
        self.assertEqual(len(ids), n)
        self.assertEqual(len(set(ids)), n)


if __name__ == "__main__":
    unittest.main()
