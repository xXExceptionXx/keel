"""Markdown backlog (F5): a change touches only the affected item; unknown fields, prose and headings survive."""
import json
import unittest

from harness import ContractTest, project, write

BACKLOG = """# Backlog

Freitext vor den Abschnitten.

## bereit

- [BL-1] Erstes
  Problem: p1
  Prio: hoch
  Akzeptanz:
    - Kriterium a
    - Kriterium b

Ein Absatz Fließtext im Abschnitt.

### Unterüberschrift

## vorgeschlagen

- [BL-2] Zweites
  Problem: p2
  Warum: w2

## in Arbeit

## erledigt

## verworfen
"""
BLOCK = ["", "- [BL-2] Zweites", "  Problem: p2", "  Warum: w2"]


def without(lines, block):
    """lines with the first occurrence of block (a run of consecutive lines) removed."""
    for i in range(len(lines) - len(block) + 1):
        if lines[i:i + len(block)] == block:
            return lines[:i] + lines[i + len(block):]
    raise AssertionError(f"block not found: {block}")


class BacklogTest(ContractTest):
    def setup_backlog(self):
        p = project()
        write(p / ".keel" / "backlog.md", BACKLOG)
        return p

    def backlog(self, p, *args):
        return self.script("backlog.py", "--project", p, *args, proj=p)

    def test_status_change_leaves_every_other_line_unchanged(self):
        p = self.setup_backlog()
        r = self.backlog(p, "status", "BL-2", "bereit")
        self.assertEqual(r.rc, 0, r)
        after = (p / ".keel" / "backlog.md").read_text(encoding="utf-8").split("\n")
        self.assertEqual(without(after, BLOCK), without(BACKLOG.split("\n"), BLOCK))
        self.assertEqual(r.json["status"], "bereit")

    def test_unknown_fields_survive_a_change(self):
        p = self.setup_backlog()
        self.assertEqual(self.backlog(p, "link", "BL-1", ".keel/work/plans/x.md").rc, 0)
        text = (p / ".keel" / "backlog.md").read_text(encoding="utf-8")
        for kept in ("Prio: hoch", "    - Kriterium a", "Ein Absatz Fließtext im Abschnitt.", "### Unterüberschrift",
                     "Freitext vor den Abschnitten."):
            self.assertIn(kept, text)
        self.assertIn("  Plan: .keel/work/plans/x.md", text)

    def test_propose_keeps_the_order_of_sections(self):
        p = self.setup_backlog()
        f = p / "neu.md"
        write(f, "---\ntitel: Neu\nproblem: p3\nwarum: w3\nherkunft: Audit\n---\n")
        r = self.backlog(p, "propose", f)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(r.json["id"], "BL-3")
        lines = (p / ".keel" / "backlog.md").read_text(encoding="utf-8").split("\n")
        heads = [l for l in lines if l.startswith("## ")]
        self.assertEqual(heads, ["## bereit", "## vorgeschlagen", "## in Arbeit", "## erledigt", "## verworfen"])
        self.assertEqual(without(lines, ["", "- [BL-3] Neu", "  Problem: p3", "  Warum: w3", "  Herkunft: Audit"]),
                         BACKLOG.split("\n"))

    def test_show_without_id_is_a_usage_error(self):
        p = self.setup_backlog()
        r = self.backlog(p, "show")
        self.assertEqual(r.rc, 2, r)
        self.assertNotIn("Traceback", r.err)

    def test_reading_still_works(self):
        p = self.setup_backlog()
        r = self.backlog(p, "list")
        self.assertEqual([(i["id"], i["status"], i["rang"]) for i in json.loads(r.out)],
                         [("BL-1", "bereit", 1), ("BL-2", "vorgeschlagen", 1)])


if __name__ == "__main__":
    unittest.main()
