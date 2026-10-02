"""integrations.git: base branch with fallback, objects of other branches."""
import subprocess

from tests.unit.base import TempTest
from keel.integrations import git


class GitIntegrationTest(TempTest):
    def setUp(self):
        super().setUp()
        self.p = self.tmp / "proj"
        (self.p / ".keel" / "adr").mkdir(parents=True)
        self.sh("init", "-q", "-b", "trunk")
        self.sh("config", "user.email", "t@t")
        self.sh("config", "user.name", "t")
        (self.p / ".keel" / "adr" / "0001-a.md").write_text("---\nstatus: Proposed\n---\n")
        self.sh("add", "-A")
        self.sh("commit", "-q", "-m", "a")

    def sh(self, *args):
        subprocess.run(["git", "-C", str(self.p), *args], check=True, capture_output=True)

    def test_base_falls_back_to_the_current_branch(self):
        self.assertEqual(git.base(self.p), "trunk")
        self.assertTrue(git.on_base(self.p))

    def test_configured_base_wins_when_it_exists(self):
        (self.p / ".keel" / "config.yaml").write_text("git:\n  base_branch: develop\n")
        self.sh("branch", "develop")
        self.sh("switch", "-q", "-c", "feature/x")
        self.assertEqual(git.base(self.p), "develop")
        self.assertFalse(git.on_base(self.p))

    def test_objects_of_another_branch(self):
        self.sh("switch", "-q", "-c", "feature/x")
        (self.p / ".keel" / "adr" / "entwurf-b.md").write_text("x\n")
        self.sh("add", "-A")
        self.sh("commit", "-q", "-m", "b")
        self.assertEqual(git.ls_tree(self.p, "trunk", ".keel/adr"), ["0001-a.md"])
        self.assertIn("Proposed", git.show(self.p, "trunk", ".keel/adr/0001-a.md"))
        self.assertIsNone(git.show(self.p, "trunk", ".keel/adr/entwurf-b.md"))
        mb = git.merge_base(self.p, "trunk", "feature/x")
        self.assertEqual(git.diff_names(self.p, mb, "feature/x", ".keel/adr"), [".keel/adr/entwurf-b.md"])
