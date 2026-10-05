"""tool-gate: the tool-call counter survives parallel calls (N1), path tricks do not get past the test protection
and the budget exception (U1, U3), the metrics folder is found in other spellings (U2)."""
import json
import os
from concurrent.futures import ThreadPoolExecutor

from harness import ContractTest, project, tool_call


class CounterTest(ContractTest):
    def test_parallel_calls_count_every_call(self):
        p = project()
        self.seed_agent(p, ref="T-tb")
        call = tool_call(p, "Read", {"file_path": str(p / "a.py")}, agent_type="keel:entwickler")
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as c:
            c.write("\nbudget:\n  tool_calls: 500\n")
        with ThreadPoolExecutor(max_workers=25) as pool:
            results = list(pool.map(lambda _: self.hook("tool-gate", call, proj=p), range(50)))
        for r in results:
            self.assertPassed(r)
        self.assertEqual(self.agent_state(p)["calls"], 50)


class TestProtectionTest(ContractTest):
    def developer(self):
        p = project()
        self.seed_agent(p, ref="T-tb")  # fixture: tests: [a.py]
        return p

    def test_spellings_of_a_test_file_are_refused(self):
        p = self.developer()
        for target in (str(p / "a.py"), str(p / "." / "a.py"), str(p) + "//a.py", str(p / "src" / ".." / "a.py"),
                       "a.py", "./a.py"):
            with self.subTest(target=target):
                r = self.hook("tool-gate", tool_call(p, "Edit", {"file_path": target}, agent_type="keel:entwickler"),
                              proj=p)
                self.assertBlocked(r)
                self.assertIn("Tests des Testers", r.json["hookSpecificOutput"]["permissionDecisionReason"])

    def test_other_files_pass(self):
        p = self.developer()
        r = self.hook("tool-gate", tool_call(p, "Edit", {"file_path": str(p / "b.py")}, agent_type="keel:entwickler"),
                      proj=p)
        self.assertPassed(r)


class BudgetExceptionTest(ContractTest):
    def test_escaping_the_work_folder_counts_against_the_budget(self):
        p = project()
        self.seed_agent(p, ref="T-tb")
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as c:
            c.write("\nbudget:\n  tool_calls: 0\n")
        inside = tool_call(p, "Write", {"file_path": str(p / ".keel" / "work" / "tasks" / "T-tb.md")},
                           agent_type="keel:entwickler")
        self.assertPassed(self.hook("tool-gate", inside, proj=p))
        escape = tool_call(p, "Write", {"file_path": str(p / ".keel" / "work" / ".." / ".." / "src" / "app.js")},
                           agent_type="keel:entwickler")
        r = self.hook("tool-gate", escape, proj=p)
        self.assertBlocked(r)
        self.assertIn("Budget erschöpft", r.json["hookSpecificOutput"]["permissionDecisionReason"])


class MetricsFolderTest(ContractTest):
    def test_other_spellings_of_the_metrics_folder_are_refused(self):
        p = project()
        self.seed_agent(p, ref="T-tb")
        home = os.path.expanduser("~")
        spellings = ["cat ~/.keel-metrics/x/events.jsonl", "cat $KEEL_METRICS_DIR/x", "cat ${KEEL_METRICS_DIR}/x",
                     f"cat {self.metrics}/x"]
        if str(self.metrics).startswith(home + os.sep):
            spellings.append("cat ~" + str(self.metrics)[len(home):] + "/x")
        for cmd in spellings:
            with self.subTest(cmd=cmd):
                r = self.hook("tool-gate", tool_call(p, "Bash", {"command": cmd}, agent_type="keel:entwickler"),
                              proj=p)
                self.assertBlocked(r)

    def test_the_coach_may_read_it(self):
        p = project()
        self.seed_agent(p, role="coach", ref="2026-10-05")
        r = self.hook("tool-gate", tool_call(p, "Bash", {"command": "cat ~/.keel-metrics/x"}, agent_type="keel:coach"),
                      proj=p)
        self.assertPassed(r)
