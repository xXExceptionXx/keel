"""store.io under parallel processes: atomic appends, locks that serialize read-modify-write, atomic replace."""
import os
import subprocess
import sys
import unittest

from tests.unit.base import TempTest
from keel.store.io import atomic_write, create_exclusive

APPEND = "from keel.store.io import append_line; import sys; append_line(sys.argv[1], sys.argv[2] * 5000)"
COUNT = """
import sys
from pathlib import Path
from keel.store.io import atomic_write, file_lock
p = Path(sys.argv[1])
with file_lock(p):
    n = int(p.read_text()) if p.exists() else 0
    atomic_write(p, str(n + 1))
"""


class IoTest(TempTest):
    def parallel(self, code, args_list):
        procs = [subprocess.Popen([sys.executable, "-c", code, *args], env=self.env()) for args in args_list]
        for p in procs:
            self.assertEqual(p.wait(timeout=60), 0)

    def test_parallel_appends_never_interleave(self):
        f = self.tmp / "log.jsonl"
        self.parallel(APPEND, [[str(f), chr(65 + i % 26)] for i in range(50)])
        lines = f.read_text().splitlines()
        self.assertEqual(len(lines), 50)
        for line in lines:
            self.assertEqual(set(line), {line[0]})
            self.assertEqual(len(line), 5000)

    def test_lock_serializes_read_modify_write(self):
        f = self.tmp / "zaehler.txt"
        self.parallel(COUNT, [[str(f)]] * 40)
        self.assertEqual(f.read_text(), "40")
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name != "metrics"], ["zaehler.txt"])

    def test_atomic_write_keeps_mode_and_leaves_no_temp_file(self):
        f = self.tmp / "x.sh"
        f.write_text("alt")
        os.chmod(f, 0o750)
        atomic_write(f, "neu")
        self.assertEqual((f.read_text(), f.stat().st_mode & 0o777), ("neu", 0o750))
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["x.sh"])

    def test_atomic_write_follows_a_symlink(self):
        real = self.tmp / "dotfiles" / "settings.json"
        real.parent.mkdir()
        real.write_text("alt")
        link = self.tmp / "settings.json"
        link.symlink_to(real)
        atomic_write(link, "neu")
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_text(), "neu")

    def test_create_exclusive(self):
        f = self.tmp / "d" / "v.md"
        self.assertTrue(create_exclusive(f, "eins"))
        self.assertFalse(create_exclusive(f, "zwei"))
        self.assertEqual(f.read_text(), "eins")


if __name__ == "__main__":
    unittest.main()
