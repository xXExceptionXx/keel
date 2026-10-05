"""A parked start (agent-gate before SubagentStart) is created atomically and does not lock a role for ten minutes
when the start never came, e.g. because the human refused the call (N2)."""
from concurrent.futures import ThreadPoolExecutor

from harness import ContractTest, agent_call, project

CALL = ("keel:entwickler", "Aufgabe: T-tb")


class PendingTest(ContractTest):
    def test_a_refused_start_does_not_lock_the_role(self):
        p = project()
        self.assertPassed(self.hook("agent-gate", agent_call(p, *CALL), proj=p))
        self.age_state(p, 60)
        r = self.hook("agent-gate", agent_call(p, *CALL), proj=p)
        self.assertPassed(r)
        orphaned = [e for e in r.events if e.get("event") == "pending_verwaist"]
        self.assertEqual(len(orphaned), 1, r.events)
        self.assertEqual(self.pending_of(p, "entwickler")[0], "T-tb")

    def test_a_fresh_start_still_blocks_a_second_one(self):
        p = project()
        self.assertPassed(self.hook("agent-gate", agent_call(p, *CALL), proj=p))
        r = self.hook("agent-gate", agent_call(p, *CALL), proj=p)
        self.assertBlocked(r)
        self.assertIn("bereits gestartet", r.json["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_running_role_blocks_although_its_start_is_older(self):
        p = project()
        self.assertPassed(self.hook("agent-gate", agent_call(p, *CALL), proj=p))
        self.seed_agent(p, agent_id="other", role="entwickler", ref="T-nach")
        self.age_state(p, 60)
        self.assertBlocked(self.hook("agent-gate", agent_call(p, *CALL), proj=p))

    def test_parallel_starts_let_exactly_one_through(self):
        p = project()
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: self.hook("agent-gate", agent_call(p, *CALL), proj=p), range(10)))
        self.assertEqual(sum(1 for r in results if not r.blocked), 1, results)

    def test_start_binds_and_clears_the_parked_reference(self):
        p = project()
        self.assertPassed(self.hook("agent-gate", agent_call(p, *CALL), proj=p))
        self.hook("agent-start", {"hook_event_name": "SubagentStart", "agent_type": "keel:entwickler",
                                  "agent_id": "a9", "cwd": str(p)}, proj=p)
        self.assertIsNone(self.pending_of(p, "entwickler"))
        self.assertEqual(self.agent_state(p, "a9")["ref"], "T-tb")
