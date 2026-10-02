"""tests/leak_check.py against throwaway repositories: what blocks a commit and what passes."""
import os
import subprocess
import sys

from tests.unit.base import REPO, TempTest

CHECK = str(REPO / "tests" / "leak_check.py")
NOREPLY = "1+octo@users.noreply.github.com"
DENYLIST = "# private\nGeheimprojekt\nMax\\s+Muster\n"
# Built from parts so this file passes its own check.
FOREIGN = "someone@" + "mail.test"
HOME = "/Users/" + "maxmuster"


class LeakCheckTest(TempTest):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.identity("octo", NOREPLY)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def identity(self, name, email):
        self.git("config", "user.name", name)
        self.git("config", "user.email", email)

    def stage(self, text, name="a.md"):
        (self.repo / name).write_text(text, encoding="utf-8")
        self.git("add", name)

    def check(self, *args, denylist=DENYLIST):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "KEEL_LEAK"))}
        env["KEEL_LEAK_DENYLIST_FILE"] = str(self.tmp / "missing")
        if denylist is not None:
            env["KEEL_LEAK_DENYLIST"] = denylist
        return subprocess.run([sys.executable, CHECK, *args], cwd=self.repo, env=env, capture_output=True, text=True)

    def assertBlocked(self, r, reason):
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn(reason, r.stderr)

    def test_clean_change_passes(self):
        self.stage("Mail an ci@example.com, Pfad /Users/x/proj, Test-Adresse t@t\n")
        r = self.check("--staged")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_private_email_identity_blocks(self):
        self.identity("octo", FOREIGN)
        self.stage("harmless\n")
        self.assertBlocked(self.check("--staged"), "author: email is not a noreply address")

    def test_denylisted_name_in_identity_blocks(self):
        self.identity("Max Muster", NOREPLY)
        self.stage("harmless\n")
        self.assertBlocked(self.check("--staged"), "author: name is on the denylist")

    def test_denylisted_word_in_content_blocks_without_echoing_it(self):
        self.stage("Erfahrung aus dem Geheimprojekt\n")
        r = self.check("--staged")
        self.assertBlocked(r, "a.md: denylist entry 1")
        self.assertNotIn("Geheimprojekt", r.stderr)

    def test_home_path_blocks(self):
        self.stage(f"log under {HOME}/projects/app\n")
        self.assertBlocked(self.check("--staged"), "a.md: home path")

    def test_foreign_email_blocks(self):
        self.stage(f"contact: {FOREIGN}\n")
        self.assertBlocked(self.check("--staged"), "a.md: email address")

    def test_secret_blocks(self):
        self.stage("key = " + "AKIA" + "ABCDEFGHIJKLMNOP\n")
        self.assertBlocked(self.check("--staged"), "a.md: AWS access key")

    def test_allow_marker_skips_the_line(self):
        self.stage(f"{FOREIGN}  <!-- leak-check: allow -->\n")
        self.assertEqual(self.check("--staged").returncode, 0)

    def test_generic_rules_run_without_denylist(self):
        self.stage(f"Geheimprojekt, contact {FOREIGN}\n")
        r = self.check("--staged", denylist=None)
        self.assertBlocked(r, "a.md: email address")
        self.assertIn("no private denylist", r.stderr)

    def test_range_checks_messages_and_removed_content_of_every_commit(self):
        self.stage("first\n")
        self.git("commit", "-q", "-m", "start")
        self.stage("Geheimprojekt\n")
        self.git("commit", "-q", "-m", "add")
        self.stage("clean\n")
        self.git("commit", "-q", "-m", "notes from Geheimprojekt")
        r = self.check("--range", "HEAD~2..HEAD")
        self.assertBlocked(r, "message: denylist entry 1")
        self.assertIn("a.md: denylist entry 1", r.stderr)

    def test_range_checks_commit_identities(self):
        self.identity("Max Muster", FOREIGN)
        self.stage("x\n")
        self.git("commit", "-q", "-m", "x")
        r = self.check("--range", "HEAD")
        self.assertBlocked(r, "author: email is not a noreply address")
        self.assertIn("committer: name is on the denylist", r.stderr)
