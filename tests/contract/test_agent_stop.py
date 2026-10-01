"""agent-stop.sh: a role may only end when its handoff is complete; missing data blocks, it never passes."""
import unittest

from harness import CRASH_PY, REPO, ContractTest, agent_call, plugin_copy, project, write


class AgentStopTest(ContractTest):
    def stop(self, p, role, ref, root=REPO, env=None):
        write(self.metrics / p.name / "state" / "agent-a1.ref", ref + "\n")
        payload = {"hook_event_name": "SubagentStop", "agent_type": f"keel:{role}", "agent_id": "a1", "cwd": str(p),
                   "last_assistant_message": "fertig"}
        return self.hook("agent-stop", payload, proj=p, root=root, env=env)

    def assertStopRefused(self, r, mentions):
        """Blocked with a decision the role can act on, not by the generic error exit."""
        self.assertEqual(r.rc, 0, r)
        self.assertEqual((r.json or {}).get("decision"), "block", r)
        self.assertIn(mentions, r.json["reason"])

    def task(self, p, tid, head):
        return write(p / ".keel" / "work" / "tasks" / f"{tid}.md", f"---\ntyp: aufgabe\nid: {tid}\n{head}---\n# {tid}\n")

    def test_recut_without_vorhaben_blocks(self):
        p = project()
        self.task(p, "T-x", "titel: X\nstatus: geplant\ntests: []\n")
        self.assertStopRefused(self.stop(p, "planer", "T-x"), "vorhaben")

    def test_recut_without_matching_plan_blocks(self):
        p = project()
        self.task(p, "T-x", "vorhaben: V-gibt-es-nicht\ntitel: X\nstatus: geplant\ntests: []\n")
        self.assertStopRefused(self.stop(p, "planer", "T-x"), "V-gibt-es-nicht")

    def test_po_plan_without_status_blocks(self):
        p = project()
        write(p / ".keel" / "work" / "plans" / "p-ohne.md", "---\ntyp: plan\nvorhaben: V20\n---\n# Plan\n")
        self.assertStopRefused(self.stop(p, "po", "p-ohne"), "Status")

    def test_reviewer_without_round_blocks(self):
        p = project()
        self.task(p, "T-r", "vorhaben: V9\ntitel: R\nstatus: review\n")
        self.assertStopRefused(self.stop(p, "reviewer", "T-r"), "review_runde")

    def test_architect_epic_without_status_blocks(self):
        p = project()
        write(p / ".keel" / "work" / "epics" / "e-x.md", "---\ntyp: epic\nepic: e-x\ntitel: E\n---\n")
        self.assertStopRefused(self.stop(p, "architekt", "epic:e-x"), "Epic-Status")

    def test_crashing_compliance_scan_blocks(self):
        p = project()
        with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as f:
            f.write("\ntest:\n  command: true\n")
        self.task(p, "T-d", "vorhaben: V9\ntitel: D\nstatus: fertig-gemeldet\nnachweis: 3 Tests grün\ntests: []\n")
        root = plugin_copy({"scripts/compliance_scan.py": CRASH_PY})
        r = self.stop(p, "entwickler", "T-d", root=root)
        self.assertStopRefused(r, "Compliance-Scan fehlgeschlagen")
        self.assertFalse((p / ".keel" / "work" / "compliance" / "T-d.scan.md").exists())

    def test_crashing_model_check_blocks_the_coach(self):
        p = project()
        write(p / ".keel" / "work" / "coach" / "2026-10-01.md",
              "---\ntyp: coachbericht\ndatum: 2026-10-01\nkennzahlen_verletzt: 0\nvorschlaege: 0\n---\n")
        root = plugin_copy({"scripts/models.py": CRASH_PY})
        self.assertBlocked(self.stop(p, "coach", "2026-10-01", root=root))

    def test_repeated_internal_failure_lets_the_role_end_and_stops_all_roles(self):
        p = project()
        write(p / ".keel" / "work" / "coach" / "2026-10-01.md",
              "---\ntyp: coachbericht\ndatum: 2026-10-01\nkennzahlen_verletzt: 0\nvorschlaege: 0\n---\n")
        root = plugin_copy({"scripts/models.py": CRASH_PY})
        for _ in range(2):
            self.assertEqual(self.stop(p, "coach", "2026-10-01", root=root).rc, 2)
        last = self.stop(p, "coach", "2026-10-01", root=root)
        self.assertEqual(last.rc, 0, last)
        self.assertIn("hook_error", [e["event"] for e in last.events])
        r = self.hook("agent-gate", agent_call(p, "keel:entwickler", "Aufgabe: T-tb"), proj=p, root=root)
        self.assertBlocked(r)
        self.assertIn("Notbremse", r.out)

    def test_complete_planning_passes(self):
        p = project()
        self.task(p, "T-x", "vorhaben: V6\ntitel: X\nstatus: geplant\ntests: []\n")
        r = self.stop(p, "planer", "T-x")
        self.assertPassed(r)
        self.assertEqual(r.events[-1]["event"], "agent_stop")


if __name__ == "__main__":
    unittest.main()
