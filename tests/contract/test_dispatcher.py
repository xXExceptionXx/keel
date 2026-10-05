"""The hook dispatcher as Claude Code calls it (System-ADR 0022): one process per event from hooks/hooks.json,
every step of the event, the first refusal wins, observers never block, and without python3 the gates close."""
import json
import subprocess
import unittest

from harness import BASH, REPO, ContractTest, Result, path_without, project, tool_call

STEPS_OF = {"PreToolUse": "pre-tool-use", "PostToolUse": "post-tool-use", "SubagentStart": "subagent-start",
            "SubagentStop": "subagent-stop", "Stop": "stop", "SessionStart": "session-start",
            "SessionEnd": "session-end", "Notification": "notification", "UserPromptSubmit": "user-prompt-submit",
            "PermissionRequest": "permission-request"}


class DispatcherTest(ContractTest):
    def event(self, name, payload, proj, path=None):
        proc = subprocess.run([BASH, str(REPO / "bin" / "keel"), "hook", name], input=json.dumps(payload),
                              capture_output=True, text=True, env=self.env(None, path), cwd=str(proj), timeout=120)
        return Result(proc, self.metrics, proj)

    def test_hooks_json_has_one_dispatcher_entry_per_event(self):
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(set(hooks), set(STEPS_OF))
        for event, entries in hooks.items():
            commands = [h["command"] for e in entries for h in e["hooks"]]
            self.assertEqual(commands, [f'"${{CLAUDE_PLUGIN_ROOT}}/bin/keel" hook {STEPS_OF[event]}'], event)

    def test_all_steps_of_an_event_run_and_the_refusal_wins(self):
        p = project()
        self.seed_agent(p, ref="T-tb")
        r = self.event("pre-tool-use", tool_call(p, "Bash", {"command": "git push -f"}, agent_type="keel:entwickler"), p)
        self.assertBlocked(r)
        self.assertTrue(r.json["hookSpecificOutput"]["permissionDecisionReason"].startswith("keel guard:"))
        self.assertEqual(self.agent_state(p)["calls"], 1)  # tool-gate counted
        self.assertEqual(r.hooklog[-1]["tool_input"]["command"], "git push -f")  # log ran
        self.assertEqual([e["hook"] for e in r.events if e["event"] == "denied"], ["guard"])

    def test_session_end_and_notification_are_logged(self):
        p = project()
        self.assertEqual(self.event("notification", {"hook_event_name": "Notification", "cwd": str(p),
                                                     "session_id": "s1", "notification_type": "idle_prompt",
                                                     "message": "wartet"}, p).rc, 0)
        r = self.event("session-end", {"hook_event_name": "SessionEnd", "cwd": str(p), "session_id": "s1",
                                       "reason": "prompt_input_exit"}, p)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual([(h["hook_event_name"], h.get("notification_type") or h.get("reason")) for h in r.hooklog],
                         [("Notification", "idle_prompt"), ("SessionEnd", "prompt_input_exit")])

    def test_without_python_the_gates_close_and_observers_let_go(self):
        p = project()
        no_python = path_without("python3")
        cases = [
            ("pre-tool-use", tool_call(p, "Read", {"file_path": "/x"}), 0),
            ("pre-tool-use", tool_call(p, "Bash", {"command": "ls"}), 2),
            ("pre-tool-use", tool_call(p, "Read", {"file_path": "/x"}, agent_type="keel:entwickler"), 2),
            ("subagent-stop", {"hook_event_name": "SubagentStop", "agent_type": "keel:tester", "cwd": str(p)}, 2),
            ("subagent-stop", {"hook_event_name": "SubagentStop", "agent_type": "", "cwd": str(p)}, 0),
            ("user-prompt-submit", {"hook_event_name": "UserPromptSubmit", "prompt": "/keel:start", "cwd": str(p)}, 2),
            ("post-tool-use", tool_call(p, "Read", {"file_path": "/x"}, agent_type="keel:entwickler"), 0),
            ("session-start", {"hook_event_name": "SessionStart", "cwd": str(p)}, 0),
        ]
        for name, payload, rc in cases:
            with self.subTest(event=name, payload=payload.get("tool_name") or payload.get("agent_type")):
                self.assertEqual(self.event(name, payload, p, path=no_python).rc, rc)

    def test_an_observer_failure_does_not_block_the_gates(self):
        p = project()
        (p / ".keel" / "config.yaml").write_text("budget:\n  context_tokens: kaputt\n")
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Read", "cwd": str(p), "session_id": "s1",
                   "transcript_path": str(self.tmp / "t.jsonl"), "tool_input": {"file_path": "/x"}}
        (self.tmp / "t.jsonl").write_text(json.dumps({"type": "assistant", "message": {
            "usage": {"input_tokens": 5}}}) + "\n")
        r = self.event("post-tool-use", payload, p)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(r.events[-1]["event"], "hook_error")
        self.assertEqual(r.events[-1]["hook"], "context-alarm")
        self.assertEqual(r.hooklog[-1]["tool_name"], "Read")


if __name__ == "__main__":
    unittest.main()
