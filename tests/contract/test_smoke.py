"""Smoke tests: the harness reaches the hooks and normal flows behave as before."""
import unittest

from harness import ContractTest, agent_call, project


class SmokeTest(ContractTest):
    def test_developer_with_tests_ready_starts(self):
        p = project()
        r = self.hook("agent-gate", agent_call(p, "keel:entwickler", "Aufgabe: T-tb"), proj=p)
        self.assertPassed(r)
        self.assertEqual(r.err, "", "a normal start writes nothing to stderr")

    def test_unknown_keel_role_is_denied(self):
        p = project()
        r = self.hook("agent-gate", agent_call(p, "keel:xyz", "Aufgabe: T-tb"), proj=p)
        self.assertBlocked(r)
        self.assertEqual(r.events[-1]["event"], "denied")

    def test_non_keel_agent_is_ignored(self):
        p = project()
        r = self.hook("agent-gate", agent_call(p, "general-purpose", "x"), proj=p)
        self.assertPassed(r)
        self.assertEqual(r.events, [])


if __name__ == "__main__":
    unittest.main()
