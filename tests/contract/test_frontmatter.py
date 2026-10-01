"""Frontmatter of handoff files: frontmatter.py get, set, dump and validate."""
import json
import unittest

from harness import ContractTest, write


class FrontmatterTest(ContractTest):
    def file(self, head, body="# Text\n"):
        return write(self.tmp / "a.md", f"---\n{head}---\n{body}")

    def dump(self, f):
        r = self.script("frontmatter.py", "dump", f)
        self.assertEqual(r.rc, 0, r)
        return json.loads(r.out)

    def test_empty_value_is_empty_text(self):
        self.assertEqual(self.dump(self.file("typ: x\nnotiz:\n"))["notiz"], "")

    def test_block_list_after_empty_key_stays_a_list(self):
        self.assertEqual(self.dump(self.file("typ: x\naufgaben:\n  - T1\n  - T2\n"))["aufgaben"], ["T1", "T2"])

    def test_unindented_block_list_is_a_list(self):
        self.assertEqual(self.dump(self.file("typ: x\naufgaben:\n- T1\n- T2\n"))["aufgaben"], ["T1", "T2"])

    def test_comment_only_value_is_empty(self):
        f = self.file("typ: x\nentscheidung:   # Nummer der gewählten Option\n")
        r = self.script("frontmatter.py", "validate", f, "--nonempty", "entscheidung")
        self.assertEqual(r.rc, 1, r)

    def test_comment_after_value_is_stripped(self):
        self.assertEqual(self.dump(self.file("status: befunde   # bestanden | befunde\n"))["status"], "befunde")

    def test_inline_list(self):
        self.assertEqual(self.dump(self.file("tests: [a.py, b.py]\n"))["tests"], ["a.py", "b.py"])


if __name__ == "__main__":
    unittest.main()
