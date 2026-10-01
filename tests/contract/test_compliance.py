"""compliance_scan.py: exit 0 frei, 3 pruefen, 4 vorlage, 5 block; 2 when it cannot scan."""
import subprocess
import unittest

from harness import ContractTest, write

AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"


class ComplianceScanTest(ContractTest):
    def repo(self):
        d = self.tmp / "repo"
        d.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init"],
                       cwd=d, check=True)
        return d

    def scan(self, d, *args):
        return self.script("compliance_scan.py", d, *args, proj=d)

    def test_clean_repo_is_free(self):
        self.assertEqual(self.scan(self.repo()).rc, 0)

    def test_secret_in_untracked_ascii_file_blocks(self):
        d = self.repo()
        write(d / "config.py", f'KEY = "{AWS_KEY}"\n')
        self.assertEqual(self.scan(d).rc, 5)

    def test_secret_in_untracked_file_with_umlaut_blocks(self):
        d = self.repo()
        write(d / "Prüfung.py", f'KEY = "{AWS_KEY}"\n')
        self.assertEqual(self.scan(d).rc, 5)

    def test_secret_in_untracked_file_with_space_blocks(self):
        d = self.repo()
        write(d / "my secret.py", f'KEY = "{AWS_KEY}"\n')
        self.assertEqual(self.scan(d).rc, 5)

    def test_not_a_repository_is_an_error(self):
        d = self.tmp / "plain"
        d.mkdir()
        write(d / "a.py", f'KEY = "{AWS_KEY}"\n')
        r = self.scan(d)
        self.assertEqual(r.rc, 2, r)

    def test_unknown_base_is_an_error(self):
        d = self.repo()
        write(d / "a.py", f'KEY = "{AWS_KEY}"\n')
        self.assertEqual(self.scan(d, "--base", "gibt-es-nicht").rc, 2)

    def test_base_without_value_is_an_error(self):
        r = self.scan(self.repo(), "--base")
        self.assertEqual(r.rc, 2, r)
        self.assertNotIn("Traceback", r.err)


if __name__ == "__main__":
    unittest.main()
