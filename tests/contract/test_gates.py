"""Error contract of the gates (System-ADR 0019): a gate that cannot check blocks, it never lets a call through."""
import unittest

from harness import REPO, ContractTest, agent_call, path_without, project, tool_call


def in_bash(hook):
    """Whether hooks/<hook>.sh still holds its own logic (sources lib.sh) instead of forwarding to bin/keel."""
    return "lib.sh" in (REPO / "hooks" / f"{hook}.sh").read_text(encoding="utf-8")


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
    def test_bash_gates_block_without_jq(self):
        # Gates still written in Bash need jq; the ones in the dispatcher (System-ADR 0022) do not.
        p = project()
        for name, payload in gate_calls(p):
            if not in_bash(name):
                continue
            with self.subTest(hook=name, event=payload["hook_event_name"]):
                r = self.hook(name, payload, proj=p, path=path_without("jq"))
                self.assertEqual(r.rc, 2, r)
                self.assertIn("keel", r.err)

    def test_dispatcher_gates_do_not_need_jq(self):
        p = project()
        for name, payload in gate_calls(p):
            if in_bash(name):
                continue
            with self.subTest(hook=name, event=payload["hook_event_name"]):
                with_jq = self.hook(name, payload, proj=project())
                without = self.hook(name, payload, proj=project(), path=path_without("jq"))
                self.assertEqual((without.rc, without.blocked), (with_jq.rc, with_jq.blocked), without)

    def test_every_gate_blocks_without_python(self):
        p = project()
        for name, payload in gate_calls(p):
            with self.subTest(hook=name, event=payload["hook_event_name"]):
                r = self.hook(name, payload, proj=p, path=path_without("python3"))
                self.assertEqual(r.rc, 2, r)

    def test_non_keel_calls_pass_without_jq(self):
        p = project()
        calls = [("tool-gate", tool_call(p, "Read", {"file_path": "/x"})),
                 ("agent-gate", agent_call(p, "general-purpose", "x")),
                 ("skill-gate", {"hook_event_name": "UserPromptSubmit", "prompt": "hallo", "cwd": str(p)})]
        for name, payload in calls:
            with self.subTest(hook=name):
                self.assertPassed(self.hook(name, payload, proj=p, path=path_without("jq")))


class BrokenInputTest(ContractTest):
    def test_every_gate_blocks_a_broken_payload(self):
        p = project()
        for name in ("guard", "agent-gate", "tool-gate", "skill-gate", "agent-stop"):
            with self.subTest(hook=name):
                r = self.hook(name, '{"tool_name": "Bash", "agent_type": "keel:entwickler", kaputt', proj=p)
                self.assertEqual(r.rc, 2, r)


class BrokenStateTest(ContractTest):
    def developer(self, p, task_bytes, config=""):
        f = p / ".keel" / "work" / "tasks" / "T-x.md"
        f.write_bytes(task_bytes)
        if config:
            with open(p / ".keel" / "config.yaml", "a", encoding="utf-8") as c:
                c.write(config)
        sd = self.runtime(p) / "state"
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "agent-a1.ref").write_text("T-x\n")
        return sd

    def test_unreadable_task_file_does_not_unlock_the_testers_files(self):
        p = project()
        self.developer(p, b"---\ntyp: aufgabe\nid: T-x\ntests: [tests/a.test.js]\n---\nK\xe4se\n")
        r = self.hook("tool-gate", tool_call(p, "Write", {"file_path": str(p / "tests" / "a.test.js")},
                                             agent_type="keel:entwickler"), proj=p)
        self.assertBlocked(r)

    def test_budget_that_is_not_a_number_blocks(self):
        p = project()
        sd = self.developer(p, b"---\ntyp: aufgabe\nid: T-x\n---\n", config="\nbudget:\n  tool_calls: sechzig\n")
        (sd / "agent-a1.calls").write_text("500\n")
        r = self.hook("tool-gate", tool_call(p, "Read", {"file_path": str(p / "a.py")}, agent_type="keel:entwickler"),
                      proj=p)
        self.assertBlocked(r)


class ObserverTest(ContractTest):
    def test_observers_let_go_and_record_a_hook_error(self):
        p = project()
        for name in ("agent-start", "context-alarm", "session-gate"):
            with self.subTest(hook=name):
                r = self.hook(name, "{kaputt", proj=p, env={"CLAUDE_PROJECT_DIR": str(p)})
                self.assertEqual(r.rc, 0, r)
                self.assertEqual(r.events[-1]["event"], "hook_error", r)
                self.assertEqual(r.events[-1]["hook"], name)

    def test_observers_let_go_without_jq(self):
        p = project()
        payload = {"hook_event_name": "SubagentStart", "agent_type": "keel:entwickler", "agent_id": "a1", "cwd": str(p)}
        r = self.hook("agent-start", payload, proj=p, path=path_without("jq"), env={"CLAUDE_PROJECT_DIR": str(p)})
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(r.events[-1]["event"], "hook_error", r)


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

    def test_remote_branch_delete_is_denied_in_long_commands(self):
        p = project()
        cmd = "; ".join(["git push origin --delete foreign/x"] * 3000)
        for i in range(10):
            with self.subTest(run=i):
                self.assertBlocked(self.hook("guard", tool_call(p, "Bash", {"command": cmd}), proj=p))


if __name__ == "__main__":
    unittest.main()
