"""frontmatter.py set never leaves a file it cannot read itself (review of PR #13), also under parallel writers."""
import subprocess
import sys
import unittest

from harness import REPO, ContractTest, project, write

TASK = "---\ntyp: aufgabe\nid: T-x\nstatus: in-arbeit\n---\nKörper\n"


class FrontmatterWriteTest(ContractTest):
    def task(self):
        p = project()
        f = p / ".keel" / "work" / "tasks" / "T-x.md"
        write(f, TASK)
        return p, f

    def test_value_with_line_breaks_reads_back(self):
        p, f = self.task()
        value = "zeile1\nzeile2\r\nmit\ttab"
        self.assertEqual(self.script("frontmatter.py", "set", f, f"nachweis={value}", proj=p).rc, 0)
        r = self.script("frontmatter.py", "dump", f, proj=p)  # JSON: text mode would fold \r\n of get
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(r.json["nachweis"], value)
        self.assertEqual(self.script("frontmatter.py", "get", f, "status", proj=p).out.strip(), "in-arbeit")

    def test_invalid_key_is_refused_and_nothing_written(self):
        p, f = self.task()
        for pair in ("mein feld=x", "prüfer=x", "=x", "a: b=x"):
            with self.subTest(pair=pair):
                r = self.script("frontmatter.py", "set", f, pair, proj=p)
                self.assertEqual(r.rc, 2, r)
                self.assertNotIn("Traceback", r.err)
                self.assertEqual(f.read_text(encoding="utf-8"), TASK)

    def test_parallel_set_keeps_every_key(self):
        p, f = self.task()
        n = 30
        procs = [subprocess.Popen([sys.executable, str(REPO / "scripts" / "frontmatter.py"), "set", str(f), f"k{i}=v{i}"],
                                  env=self.env(), stderr=subprocess.PIPE) for i in range(n)]
        for proc in procs:
            _, err = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0, err)
        r = self.script("frontmatter.py", "dump", f, proj=p)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual({k: r.json[k] for k in r.json if k.startswith("k")}, {f"k{i}": f"v{i}" for i in range(n)})


if __name__ == "__main__":
    unittest.main()
