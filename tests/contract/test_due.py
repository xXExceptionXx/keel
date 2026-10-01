"""Due items and briefing (due.py, briefing_needed.py): exit 0 no, 1 yes, 2 cannot tell; consumers fail closed."""
import unittest

from harness import CRASH_PY, ContractTest, agent_call, plugin_copy, project, write


class DueContractTest(ContractTest):
    def broken_adr(self, p):
        """An ADR that is not UTF-8: reading it makes briefing_needed.py fail."""
        f = p / ".keel" / "adr" / "0001-kaputt.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"---\ntitel: \xff\xfe\n---\n")
        return f

    def test_event_without_timestamp_is_skipped(self):
        p = project()
        write(self.runtime(p) / "events.jsonl", '{"event":"agent_stop","role":"tester"}\n')
        r = self.script("due.py", p, "--json", proj=p)
        self.assertIn(r.rc, (0, 1), r)
        self.assertNotIn("Traceback", r.err)

    def test_missing_argument_is_an_error(self):
        self.assertEqual(self.script("due.py").rc, 2)
        self.assertEqual(self.script("briefing_needed.py").rc, 2)

    def test_unreadable_adr_is_an_error_not_a_briefing(self):
        p = project()
        self.broken_adr(p)
        r = self.script("briefing_needed.py", p, proj=p)
        self.assertEqual(r.rc, 2, r)

    def test_due_reports_a_failing_briefing_check(self):
        p = project()
        self.broken_adr(p)
        r = self.script("due.py", p, "--json", proj=p)
        self.assertEqual(r.rc, 2, r)

    def test_role_start_is_denied_when_due_items_cannot_be_checked(self):
        p = project()
        root = plugin_copy({"scripts/due.py": CRASH_PY})
        r = self.hook("agent-gate", agent_call(p, "keel:entwickler", "Aufgabe: T-tb"), proj=p, root=root)
        self.assertBlocked(r)
        self.assertIn("Fälligkeiten", r.out + r.err)

    def test_start_command_is_blocked_when_briefing_cannot_be_checked(self):
        p = project()
        self.broken_adr(p)
        r = self.hook("skill-gate", {"hook_event_name": "UserPromptSubmit", "prompt": "/keel:start", "cwd": str(p),
                                     "session_id": "s1"}, proj=p)
        self.assertBlocked(r)

    def test_session_start_reports_a_failing_due_check(self):
        p = project()
        root = plugin_copy({"scripts/due.py": CRASH_PY})
        r = self.hook("session-gate", {"hook_event_name": "SessionStart", "cwd": str(p), "session_id": "s1"},
                      proj=p, root=root)
        self.assertEqual(r.rc, 0, r)
        context = r.json["hookSpecificOutput"]["additionalContext"]
        self.assertIn("nicht prüfbar", context)


if __name__ == "__main__":
    unittest.main()
