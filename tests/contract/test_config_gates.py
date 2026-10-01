"""A configuration the codec refuses never opens a gate (review of PR #13): the test gate cannot report green,
and the compliance scan never loses a project pattern to an escape it does not understand."""
import subprocess
import unittest

from harness import ContractTest, project, write

BROKEN = {
    "tab": 'test:\n  command: "false"\n\ttimeout: 60\n',
    "text after quote": 'test:\n  command: "false"\nnotiz: "a" b\n',
}


class GateConfigTest(ContractTest):
    def test_gate_with_unreadable_config_cannot_check(self):
        for name, text in BROKEN.items():
            with self.subTest(config=name):
                p = project()
                write(p / ".keel" / "config.yaml", text)
                r = self.script("gate.sh", p, "probe", proj=p)
                self.assertEqual(r.rc, 2, r)
                self.assertNotIn("grün", r.out)
                self.assertIn("config.yaml:3", r.err)


class CompliancePatternTest(ContractTest):
    def repo(self, config):
        d = self.tmp / "repo"
        d.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init"],
                       cwd=d, check=True)
        write(d / ".keel" / "config.yaml", config)
        write(d / "app.js", 'const kundennummer = 1;\n')
        return d

    def test_regex_in_single_quotes_is_found(self):
        d = self.repo("compliance:\n  pii_patterns: '\\bkundennummer\\b'\n")
        r = self.script("compliance_scan.py", d, proj=d)
        self.assertEqual(r.rc, 3, r)

    def test_unknown_escape_in_double_quotes_cannot_scan(self):
        d = self.repo('compliance:\n  pii_patterns: "\\bkundennummer\\b"\n')
        r = self.script("compliance_scan.py", d, proj=d)
        self.assertEqual(r.rc, 2, r)
        self.assertIn("config.yaml:2", r.err)

    def test_pattern_list_cannot_scan(self):
        d = self.repo("compliance:\n  pii_patterns: [a, b]\n")
        r = self.script("compliance_scan.py", d, proj=d)
        self.assertEqual(r.rc, 2, r)
        self.assertNotIn("Traceback", r.err)
        self.assertIn("pii_patterns", r.err)


if __name__ == "__main__":
    unittest.main()
