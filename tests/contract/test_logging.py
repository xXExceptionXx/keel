"""Raw data for the learning loop: the hook log, events, and the Lead's context alarm."""
import json
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor

from harness import BASH, REPO, ContractTest, agent_call, project, tool_call, write


class ContextAlarmTest(ContractTest):
    def transcript(self, used_tokens, size_kb):
        line = json.dumps({"type": "user", "message": {"content": "x" * 900}})
        lines = [line] * size_kb
        lines.append(json.dumps({"type": "assistant", "message": {"model": "m", "usage": {
            "input_tokens": used_tokens, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}))
        return write(self.tmp / "t.jsonl", "\n".join(lines) + "\n")

    @unittest.expectedFailure
    def test_alarm_fires_on_a_large_transcript(self):
        p = project()
        t = self.transcript(150000, 300)
        r = self.hook("context-alarm", {"hook_event_name": "PostToolUse", "transcript_path": str(t), "session_id": "s1",
                                        "cwd": str(p), "tool_name": "Read"}, proj=p)
        self.assertEqual(r.rc, 0, r)
        self.assertIn("75 %", r.json["hookSpecificOutput"]["additionalContext"])

    def test_no_alarm_below_the_threshold(self):
        p = project()
        t = self.transcript(20000, 10)
        r = self.hook("context-alarm", {"hook_event_name": "PostToolUse", "transcript_path": str(t), "session_id": "s1",
                                        "cwd": str(p), "tool_name": "Read"}, proj=p)
        self.assertPassed(r)
        self.assertIsNone(r.json)


class HookLogTest(ContractTest):
    def run_parallel(self, name, payloads, proj):
        def one(payload):
            return subprocess.run([BASH, str(REPO / "hooks" / f"{name}.sh")], input=json.dumps(payload), text=True,
                                  capture_output=True, env=self.env(), cwd=str(proj))
        with ThreadPoolExecutor(max_workers=25) as pool:
            return list(pool.map(one, payloads))

    @unittest.expectedFailure
    def test_parallel_large_payloads_give_valid_trimmed_lines(self):
        p = project()
        payloads = []
        for i in range(50):
            payload = tool_call(p, "Bash", {"command": f"echo {i}"})
            payload.update({"hook_event_name": "PostToolUse", "tool_response": {"stdout": "y" * 100_000}})
            payloads.append(payload)
        self.run_parallel("log", payloads, p)
        lines = (self.metrics / p.name / "hooks.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 50)
        records = [json.loads(line) for line in lines]
        self.assertEqual(sorted(r["tool_input"]["command"] for r in records), sorted(f"echo {i}" for i in range(50)))
        self.assertTrue(all("tool_response" not in r and "ts" in r for r in records))

    def test_parallel_denies_give_valid_events(self):
        p = project()
        self.run_parallel("agent-gate", [agent_call(p, "keel:xyz", f"Aufgabe: T{i}") for i in range(50)], p)
        events = [json.loads(line) for line in
                  (self.metrics / p.name / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len([e for e in events if e["event"] == "denied"]), 50)

    @unittest.expectedFailure
    def test_typed_keel_commands_reach_the_log(self):
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        commands = [h["command"] for entry in hooks["UserPromptSubmit"] for h in entry["hooks"]]
        self.assertTrue(any("log.sh" in c for c in commands), commands)

    @unittest.expectedFailure
    def test_skill_and_prompt_are_kept(self):
        p = project()
        self.hook("log", {"hook_event_name": "UserPromptSubmit", "prompt": "/keel:start " + "z" * 2000,
                          "cwd": str(p), "session_id": "s1"}, proj=p)
        self.hook("log", tool_call(p, "Skill", {"skill": "keel:vorhaben", "args": "x"}), proj=p)
        prompt, skill = (self.metrics / p.name / "hooks.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertTrue(json.loads(prompt)["prompt"].startswith("/keel:start"))
        self.assertLessEqual(len(json.loads(prompt)["prompt"]), 500)
        self.assertEqual(json.loads(skill)["tool_input"]["skill"], "keel:vorhaben")


if __name__ == "__main__":
    unittest.main()
