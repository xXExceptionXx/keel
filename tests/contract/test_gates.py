"""Error contract of the gates (System-ADR 0019): a gate that cannot check blocks, it never lets a call through."""
import unittest

from harness import ContractTest, agent_call, path_without, project, tool_call


def gate_calls(p):
    """One keel payload per gate: (hook, payload)."""
    return [
        ("guard", tool_call(p, "Bash", {"command": "ls"})),
        ("agent-gate", agent_call(p, "keel:entwickler", "Aufgabe: T-tb")),
        ("tool-gate", tool_call(p, "Read", {"file_path": str(p / "a.py")}, agent_type="keel:entwickler")),
        ("skill-gate", {"hook_event_name": "PreToolUse", "tool_name": "Skill", "cwd": str(p), "session_id": "s1",
                        "tool_input": {"skill": "keel:start"}}),
        ("skill-gate", {"hook_event_name": "UserPromptSubmit", "prompt": "/keel:start", "cwd": str(p), "session_id": "s1"}),
        ("agent-stop", {"hook_event_name": "SubagentStop", "agent_type": "keel:entwickler", "agent_id": "a1",
                        "cwd": str(p), "last_assistant_message": "fertig"}),
    ]


class MissingToolsTest(ContractTest):
    @unittest.expectedFailure
    def test_every_gate_blocks_without_jq(self):
        p = project()
        for name, payload in gate_calls(p):
            with self.subTest(hook=name, event=payload["hook_event_name"]):
                r = self.hook(name, payload, proj=p, path=path_without("jq"))
                self.assertEqual(r.rc, 2, r)
                self.assertIn("keel", r.err)

    @unittest.expectedFailure
    def test_every_gate_blocks_without_python(self):
        p = project()
        for name, payload in gate_calls(p):
            with self.subTest(hook=name, event=payload["hook_event_name"]):
                r = self.hook(name, payload, proj=p, path=path_without("python3"))
                self.assertEqual(r.rc, 2, r)

    @unittest.expectedFailure
    def test_non_keel_calls_pass_without_jq(self):
        p = project()
        calls = [("tool-gate", tool_call(p, "Read", {"file_path": "/x"})),
                 ("agent-gate", agent_call(p, "general-purpose", "x")),
                 ("skill-gate", {"hook_event_name": "UserPromptSubmit", "prompt": "hallo", "cwd": str(p)})]
        for name, payload in calls:
            with self.subTest(hook=name):
                self.assertPassed(self.hook(name, payload, proj=p, path=path_without("jq")))


class BrokenInputTest(ContractTest):
    @unittest.expectedFailure
    def test_every_gate_blocks_a_broken_payload(self):
        p = project()
        for name in ("guard", "agent-gate", "tool-gate", "skill-gate", "agent-stop"):
            with self.subTest(hook=name):
                r = self.hook(name, '{"tool_name": "Bash", "agent_type": "keel:entwickler", kaputt', proj=p)
                self.assertEqual(r.rc, 2, r)


class TempFilesTest(ContractTest):
    def test_no_temp_files_left_after_a_deny(self):
        p = project()
        r = self.hook("agent-gate", agent_call(p, "keel:entwickler", "Aufgabe: T-fehlt"), proj=p)
        self.assertBlocked(r)
        self.assertEqual(list(self.tmpdir.iterdir()), [])


class LargeInputTest(ContractTest):
    def test_metrics_folder_is_denied_with_large_input(self):
        p = project()
        payload = tool_call(p, "Read", {"file_path": str(self.metrics / "x" / "events.jsonl"), "pad": "x" * 1_000_000},
                            agent_type="keel:entwickler")
        for i in range(10):
            with self.subTest(run=i):
                self.assertBlocked(self.hook("tool-gate", payload, proj=p))

    @unittest.expectedFailure
    def test_remote_branch_delete_is_denied_in_long_commands(self):
        p = project()
        cmd = "; ".join(["git push origin --delete foreign/x"] * 3000)
        for i in range(10):
            with self.subTest(run=i):
                self.assertBlocked(self.hook("guard", tool_call(p, "Bash", {"command": cmd}), proj=p))


if __name__ == "__main__":
    unittest.main()
