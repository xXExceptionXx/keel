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



class RoundTripTest(ContractTest):
    VALUES = ['Er sagt "hi": a #b \\ x', '"zitiert" am Anfang', "it's: fine", "a: b", "C:\\pfad\\datei", "#kein Kommentar"]

    def test_values_survive_repeated_writes_of_other_fields(self):
        f = write(self.tmp / "a.md", "---\ntyp: x\n---\n# Text\n")
        for i, v in enumerate(self.VALUES):
            self.assertEqual(self.script("frontmatter.py", "set", f, f"k{i}={v}").rc, 0)
        for n in range(10):
            self.assertEqual(self.script("frontmatter.py", "set", f, f"other={n}").rc, 0)
        data = json.loads(self.script("frontmatter.py", "dump", f).out)
        for i, v in enumerate(self.VALUES):
            with self.subTest(value=v):
                self.assertEqual(data[f"k{i}"], v)
        self.assertTrue(f.read_text(encoding="utf-8").endswith("# Text\n"))


if __name__ == "__main__":
    unittest.main()
