"""Review verdict (System-ADR 0018): review.py pruefen against review files of two rounds."""
import unittest

from harness import ContractTest, project, write


def review_file(task, runde, rows, status="befunde", counts=None):
    n = {s: sum(1 for r in rows if r[0] == s) for s in ("blockierend", "wichtig", "anmerkung")}
    n.update(counts or {})
    head = "".join(f"{k}: {v}\n" for k, v in n.items())
    table = "".join(f"| {s} | {h} | src/a.py:{i} | Befund {i} |\n" for i, (s, h) in enumerate(rows, 1))
    return (f"---\ntyp: review\naufgabe: {task}\nrunde: {runde}\nstatus: {status}\n{head}---\n\n"
            f"| Schweregrad | Herkunft | Fundstelle | Beschreibung |\n| --- | --- | --- | --- |\n{table}")


class ReviewVerdictTest(ContractTest):
    def setUp(self):
        super().setUp()
        self.p = project()
        self.tasks = self.p / ".keel" / "work" / "tasks"
        self.reviews = self.p / ".keel" / "work" / "reviews"
        write(self.tasks / "T1.md", "---\ntyp: aufgabe\nid: T1\nvorhaben: V9\ntitel: T\nstatus: review\nreview_runde: 2\n---\n")

    def verdict(self, before, now):
        """before/now: (blockierend, wichtig) of round 1 and round 2."""
        r1 = [("blockierend", "neu")] * before[0] + [("wichtig", "neu")] * before[1]
        r2 = [("blockierend", "fix")] * now[0] + [("wichtig", "fix")] * now[1]
        write(self.reviews / "T1-r1.md", review_file("T1", 1, r1))
        write(self.reviews / "T1-r2.md", review_file("T1", 2, r2))
        r = self.script("review.py", "pruefen", self.p, "T1", proj=self.p)
        self.assertEqual(r.rc, 0, r)
        return self.script("frontmatter.py", "get", self.tasks / "T1.md", "review_ergebnis").out.strip()

    def test_shift_from_blocking_to_important_does_not_count_as_sinking(self):
        self.assertEqual(self.verdict((1, 0), (0, 9)), "vorlage")

    def test_blocking_turned_into_fewer_important_findings_means_rework(self):
        self.assertEqual(self.verdict((4, 0), (0, 2)), "nacharbeit")

    def test_blocking_turned_into_one_important_finding_means_rework(self):
        self.assertEqual(self.verdict((1, 0), (0, 1)), "nacharbeit")

    def test_rising_sum_despite_fewer_blockers_goes_to_a_decision(self):
        self.assertEqual(self.verdict((1, 1), (0, 5)), "vorlage")

    def test_fewer_findings_in_one_category_means_rework(self):
        self.assertEqual(self.verdict((2, 1), (1, 1)), "nacharbeit")

    def test_equal_findings_go_to_a_decision(self):
        self.assertEqual(self.verdict((1, 1), (1, 1)), "vorlage")

    def test_rising_findings_go_to_a_decision(self):
        self.assertEqual(self.verdict((1, 1), (1, 2)), "vorlage")

    @unittest.expectedFailure
    def test_empty_count_field_is_a_validation_error_not_a_crash(self):
        text = review_file("T1", 2, [("wichtig", "fix")]).replace("anmerkung: 0\n", "anmerkung:\n")
        write(self.reviews / "T1-r2.md", text)
        write(self.reviews / "T1-r1.md", review_file("T1", 1, [("wichtig", "neu"), ("wichtig", "neu")]))
        r = self.script("review.py", "pruefen", self.p, "T1", proj=self.p)
        self.assertEqual(r.rc, 1, r)
        self.assertNotIn("Traceback", r.err)
        self.assertIn("anmerkung", r.err)


if __name__ == "__main__":
    unittest.main()
