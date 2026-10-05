"""Time budget only reports (System-ADR 0021, project ADR 0023): one budget_slow per run, never a refusal."""
import time

from harness import ContractTest, project, tool_call


class BudgetSlowTest(ContractTest):
    def run_over_time(self):
        p = project()
        (p / ".keel" / "work" / "tasks" / "T-x.md").write_text("---\ntyp: aufgabe\nid: T-x\n---\n")
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as c:
            c.write("\nbudget:\n  minutes: 1\n")
        self.seed_agent(p, ref="T-x", start=int(time.time()) - 600)
        return p

    def test_a_run_over_the_limit_reports_once_and_is_not_refused(self):
        p = self.run_over_time()
        call = tool_call(p, "Edit", {"file_path": str(p / "src" / "a.js")}, agent_type="keel:entwickler")
        first = self.hook("tool-gate", call, proj=p)
        second = self.hook("tool-gate", call, proj=p)
        self.assertPassed(first)
        self.assertPassed(second)
        slow = [e for e in second.events if e.get("event") == "budget_slow"]
        self.assertEqual(len(slow), 1, second.events)
        self.assertEqual((slow[0]["role"], slow[0]["ref"], slow[0]["limit"]), ("entwickler", "T-x", 1))
        self.assertGreaterEqual(slow[0]["minutes"], 10)
        self.assertFalse([e for e in second.events if e.get("event") in ("budget_exhausted", "denied")])

    def test_the_marker_keeps_the_report_to_one_and_the_task_stays_untouched(self):
        p = self.run_over_time()
        self.hook("tool-gate", tool_call(p, "Read", {"file_path": str(p / "a.js")}, agent_type="keel:entwickler"),
                  proj=p)
        self.assertTrue(self.agent_state(p)["slow"])
        task = (p / ".keel" / "work" / "tasks" / "T-x.md").read_text()
        self.assertNotIn("budget-erschoepft", task)
