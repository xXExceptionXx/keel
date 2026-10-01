"""store.codec and store.frontmatter: the rules of work package 1 and F7, round trips, refusals with line numbers."""
import unittest

from tests.unit.base import TempTest
from keel.domain.errors import ParseError
from keel.store import codec, frontmatter

TRICKY = ["zeile1\nzeile2", "cr\rlf", "tab\tda", "glocke\x07", "\x08b", "\\bwort\\b", "😀 emoji",
          'Er sagt "Hallo": ok', "a: b", "x # y", "back\\slash", "'führend", "C:\\Pfad\\datei", "ende ", " anfang",
          "true", "null", "[klammer]", "{x}", "|", ">", "&anker", "*stern", "!tag", "a, b", "#", "-", "- x", "ü ß €"]


class CodecTest(unittest.TestCase):
    def test_scalars_and_quotes(self):
        d = codec.loads('a: plain text\nb: "o/r#1"  # c\nc: \'it\'\'s\'\nd: a#b\ne: x # comment\nf:\ng: # nur Kommentar\n'
                        'h: ""\n')
        self.assertEqual(d, {"a": "plain text", "b": "o/r#1", "c": "it's", "d": "a#b", "e": "x", "f": "", "g": "",
                             "h": ""})

    def test_nesting_and_lists(self):
        text = ("backlog:\n  github:\n    repo: o/r\n    labels:\n      bereit: \"keel:bereit\"\n"
                "liste:\n  - a\n  - \"b, c\"\nkompakt:\n- x\n- y\ninline: [a, \"b, c\", 'd''e']\nleer: []\n")
        self.assertEqual(codec.loads(text), {
            "backlog": {"github": {"repo": "o/r", "labels": {"bereit": "keel:bereit"}}},
            "liste": ["a", "b, c"], "kompakt": ["x", "y"], "inline": ["a", "b, c", "d'e"], "leer": []})

    def test_comments_and_blank_lines_anywhere(self):
        self.assertEqual(codec.loads("# k\na:\n  # k\n\n  b: 1   # k\n# github:\n#   repo: x\n"), {"a": {"b": "1"}})

    def test_no_anchors_or_tags(self):
        self.assertEqual(codec.loads("a: &anker x\nb: *Entwurf*\nc: !wichtig\n"),
                         {"a": "&anker x", "b": "*Entwurf*", "c": "!wichtig"})

    def test_escapes(self):
        d = codec.loads('a: "zeile\\nzwei \\"q\\" \\\\ \\/ \\u00e4 \\ud83d\\ude00"\nb: \'\\bwort\\b\'\n')
        self.assertEqual(d, {"a": 'zeile\nzwei "q" \\ / ä 😀', "b": "\\bwort\\b"})

    def test_section_written_twice_is_merged(self):
        self.assertEqual(codec.loads("t:\n  a: 1\n  b: 2\nt:\n  b: 3\n"), {"t": {"a": "1", "b": "3"}})

    def test_refusals_name_the_line(self):
        cases = {
            "a: 1\n\tb: 2\n": 2,
            "a: {x: 1}\n": 1,
            "a: |\n  text\n": 1,
            "a: 1\n  b: 2\n": 2,
            "a:\n  - x\n    - y\n": 3,
            'a: "\\bwort\\b"\n': 1,
            'a: "C:\\Pfad"\n': 1,
            'a: "\\u12"\n': 1,
            "kein feld\n": 1,
            "- x\n": 1,
            "a: [x, \n": 1,
            "a: \"offen\n": 1,
            "a: \"zu\" mehr\n": 1,
            "a: [x, [y]]\n": 1,
            "a: [x, , y]\n": 1,
            "x: 1\nPrüfer: y\n": 2,
        }
        for text, line in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(ParseError) as ctx:
                    codec.loads(text, source="f.yaml")
                self.assertEqual(ctx.exception.line, line)
                self.assertIn(f"f.yaml:{line}:", str(ctx.exception))

    def test_dump_round_trip(self):
        data = {f"k{i}": v for i, v in enumerate(TRICKY)}
        data["liste"] = TRICKY
        data["einfach"] = ["a.py", "b/c.md"]
        data["tief"] = {"x": {"y": "z", "l": ["1", "zwei drei"]}}
        self.assertEqual(codec.loads(codec.dumps(data)), data)
        self.assertIn("einfach: [a.py, b/c.md]", codec.dumps(data))


class FrontmatterTest(TempTest):
    def test_parse_render_keeps_order_and_body(self):
        text = "---\nzwei: 2\neins: \"Er sagt \\\"Hallo\\\": ok\"\nliste: [a, b]\n---\n# Titel\n\nText --- mit Strichen\n"
        data, body = frontmatter.parse(text)
        self.assertEqual(data["__order__"], ["zwei", "eins", "liste"])
        self.assertEqual(data["eins"], 'Er sagt "Hallo": ok')
        self.assertEqual(frontmatter.render(data, body), text)

    def test_no_frontmatter(self):
        self.assertEqual(frontmatter.parse("# nur Text\n"), (None, "# nur Text\n"))
        data, body = frontmatter.parse("---\na: 1\n---")
        self.assertEqual((data["a"], body), ("1", ""))

    def test_line_numbers_count_from_the_file(self):
        with self.assertRaises(ParseError) as ctx:
            frontmatter.parse("---\na: 1\nkaputt\n---\n", source="x.md")
        self.assertEqual(ctx.exception.line, 3)

    def test_update_survives_many_writes(self):
        f = self.tmp / "t.md"
        f.write_text("---\ntyp: aufgabe\n" + "".join(f"k{i}: {codec.dump_scalar(v)}\n" for i, v in enumerate(TRICKY))
                     + "---\nKörper\n", encoding="utf-8")
        for n in range(10):
            frontmatter.update(f, {"zaehler": str(n)})
        data, body = frontmatter.load(f)
        for i, v in enumerate(TRICKY):
            self.assertEqual(data[f"k{i}"], v)
        self.assertEqual((data["zaehler"], body), ("9", "Körper\n"))

    def test_tolerant_reading(self):
        bad = self.tmp / "bad.md"
        bad.write_bytes(b"---\na: \xff\n---\n")
        broken = self.tmp / "broken.md"
        broken.write_text("---\nkaputt\n---\n", encoding="utf-8")
        for f in (bad, broken, self.tmp / "fehlt.md"):
            self.assertEqual(frontmatter.fields_tolerant(f), {})
            self.assertIsNone(frontmatter.load_tolerant(f))


if __name__ == "__main__":
    unittest.main()
