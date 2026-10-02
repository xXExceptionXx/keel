"""agent-stop finds plans and ADRs by their frontmatter through the codec, not by grep (review of PR #13): a
quoted value or a trailing comment is the same value."""
import unittest

from harness import ContractTest, project, write


class FrontmatterLookupTest(ContractTest):
    def stop(self, p, role, ref):
        write(self.runtime(p) / "state" / "agent-a1.ref", ref + "\n")
        self.adr_snapshot(p)
        payload = {"hook_event_name": "SubagentStop", "agent_type": f"keel:{role}", "agent_id": "a1", "cwd": str(p),
                   "last_assistant_message": "fertig"}
        return self.hook("agent-stop", payload, proj=p)

    def test_plan_with_quoted_vorhaben_is_found(self):
        p = project()
        plan = p / ".keel" / "work" / "plans" / "p-geplant.md"
        write(plan, plan.read_text(encoding="utf-8").replace("vorhaben: V6", 'vorhaben: "V6"  # Kommentar'))
        write(p / ".keel" / "work" / "tasks" / "T-x.md",
              "---\ntyp: aufgabe\nid: T-x\nvorhaben: V6\ntitel: X\nstatus: geplant\ntests: []\n---\n# T-x\n")
        self.assertPassed(self.stop(p, "planer", "T-x"))

    def test_find_command(self):
        p = project()
        plans = p / ".keel" / "work" / "plans"
        r = self.script("frontmatter.py", "find", plans, "vorhaben=V6", "typ=plan", proj=p)
        self.assertEqual((r.rc, r.out.strip()), (0, str(plans / "p-geplant.md")))
        self.assertEqual(self.script("frontmatter.py", "find", plans, "vorhaben=V99", proj=p).rc, 1)
        write(plans / "kaputt.md", "---\nkein feld\n---\n")
        r = self.script("frontmatter.py", "find", plans, "vorhaben=V6", proj=p)
        self.assertEqual(r.rc, 2, r)
        self.assertIn("kaputt.md:2", r.err)


if __name__ == "__main__":
    unittest.main()
