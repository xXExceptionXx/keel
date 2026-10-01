"""store.paths: one runtime folder per project (N4), the same key for every way to name the project."""
import os
import subprocess
import sys
import unittest

from tests.unit.base import TempTest
from keel.store.paths import Paths, project_key

ENSURE = "from keel.store.paths import Paths; import sys; Paths(sys.argv[1]).ensure()"


class PathsTest(TempTest):
    def test_projects_with_the_same_name_are_separate(self):
        a, b = self.tmp / "a" / "app", self.tmp / "b" / "app"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        self.assertNotEqual(Paths(a).runtime, Paths(b).runtime)
        self.assertTrue(Paths(a).runtime.name.startswith("app-"))
        self.assertEqual(Paths(a).runtime.parent, self.tmp / "metrics")

    def test_symlink_and_relative_paths_give_the_same_key(self):
        real = self.tmp / "real" / "proj"
        real.mkdir(parents=True)
        link = self.tmp / "link"
        link.symlink_to(real)
        self.assertEqual(project_key(link), project_key(real))
        old = os.getcwd()
        os.chdir(real)
        try:
            self.assertEqual(project_key("."), project_key(real))
        finally:
            os.chdir(old)

    def test_spelling_of_a_case_insensitive_file_system(self):
        real = self.tmp / "Proj"
        real.mkdir()
        other = self.tmp / "proj"
        if not other.exists():
            self.skipTest("file system is case-sensitive")
        self.assertEqual(project_key(other), project_key(real))
        self.assertEqual(Paths(str(other).upper()).project, real)
        self.assertTrue(Paths(other).runtime.name.startswith("Proj-"))

    def test_layout(self):
        p = Paths(self.tmp)
        self.assertEqual(p.state, p.runtime / "state")
        self.assertEqual(p.events, p.runtime / "events.jsonl")
        self.assertEqual(p.brake, p.state / "kern-gesperrt")
        self.assertFalse(p.runtime.exists())
        p.ensure()
        self.assertTrue(p.state.is_dir() and p.logs.is_dir())

    def test_parallel_first_access(self):
        procs = [subprocess.Popen([sys.executable, "-c", ENSURE, str(self.tmp)], env=self.env()) for _ in range(20)]
        self.assertEqual([p.wait(timeout=60) for p in procs], [0] * 20)
        self.assertEqual([d.name for d in (self.tmp / "metrics").iterdir()], [Paths(self.tmp).key])


if __name__ == "__main__":
    unittest.main()
