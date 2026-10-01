"""One codec for configuration and frontmatter (F7): quotes, comments, nesting, lists; anything else is refused
with its line number."""
import unittest

from harness import ContractTest, project, write

CONFIG = """# Kommentar
motor:
  repo: "o/r#1"   # Kommentar nach Anführungszeichen
backlog:
  provider: github
  github:
    repo: o/r
    labels:
      bereit: "keel:bereit"
      in_arbeit: 'keel:in-arbeit'
test:
  command: make test
  extra:
    - a
    - "b, c"
  andere: [x, "y # kein Kommentar"]
"""


class ConfigCodecTest(ContractTest):
    def config(self, p, key, default=""):
        return self.script("config.py", p, key, default, proj=p)

    def test_hash_inside_quotes_is_not_a_comment(self):
        p = project()
        write(p / ".keel" / "config.yaml", CONFIG)
        self.assertEqual(self.config(p, "motor.repo").out.strip(), "o/r#1")

    def test_three_levels_and_lists(self):
        p = project()
        write(p / ".keel" / "config.yaml", CONFIG)
        self.assertEqual(self.config(p, "backlog.github.repo").out.strip(), "o/r")
        self.assertEqual(self.config(p, "backlog.github.labels.bereit").out.strip(), "keel:bereit")
        self.assertEqual(self.config(p, "backlog.github.labels.in_arbeit").out.strip(), "keel:in-arbeit")
        self.assertEqual(self.config(p, "test.command").out.strip(), "make test")
        self.assertEqual(self.config(p, "test.extra", "liste").out.strip(), "liste")  # not a scalar: the default

    def test_unknown_syntax_in_the_config_is_refused_with_its_line(self):
        p = project()
        write(p / ".keel" / "config.yaml", "budget:\n  tool_calls: 60\n  minutes: {a: 1}\n")
        r = self.config(p, "budget.tool_calls", "60")
        self.assertEqual(r.rc, 2, r)
        self.assertRegex(r.err, r"config\.yaml:3\b")
        self.assertNotIn("Traceback", r.err)

    def test_missing_arguments_are_a_usage_error(self):
        r = self.script("config.py")
        self.assertEqual(r.rc, 2, r)
        self.assertNotIn("Traceback", r.err)

    def test_unknown_line_in_frontmatter_is_refused_with_its_line(self):
        p = project()
        f = p / "x.md"
        write(f, "---\ntyp: aufgabe\ndas ist kein Feld\n---\nText\n")
        r = self.script("frontmatter.py", "get", f, "typ", proj=p)
        self.assertEqual(r.rc, 2, r)
        self.assertRegex(r.err, r"x\.md:3\b")


if __name__ == "__main__":
    unittest.main()
