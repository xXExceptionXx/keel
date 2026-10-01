"""Runtime folder per project (N4): two projects with the same folder name share nothing."""
import shutil
import unittest

from harness import ContractTest, agent_call, project


class RuntimeKeyTest(ContractTest):
    def two_apps(self):
        apps = []
        for parent in ("a", "b"):
            dst = self.tmp / parent / "app"
            shutil.copytree(project(), dst, symlinks=True)
            apps.append(dst)
        return apps

    def test_hook_logs_are_separate(self):
        a, b = self.two_apps()
        for p in (a, b):
            r = self.hook("log", {"hook_event_name": "UserPromptSubmit", "prompt": "hallo", "cwd": str(p)}, proj=p)
            self.assertEqual(r.rc, 0, r)
        logs = sorted(self.metrics.rglob("hooks.jsonl"))
        self.assertEqual(len(logs), 2, logs)
        for f in logs:
            cwds = {line.split('"cwd":"')[1].split('"')[0] for line in f.read_text(encoding="utf-8").splitlines()}
            self.assertEqual(len(cwds), 1, cwds)

    def test_a_starting_role_in_one_project_does_not_block_the_other(self):
        a, b = self.two_apps()
        self.assertPassed(self.hook("agent-gate", agent_call(a, "keel:entwickler", "Aufgabe: T-tb"), proj=a))
        self.assertPassed(self.hook("agent-gate", agent_call(b, "keel:entwickler", "Aufgabe: T-tb"), proj=b))

    def test_runtime_folders_differ(self):
        a, b = self.two_apps()
        self.assertNotEqual(self.runtime(a), self.runtime(b))
        self.assertTrue(self.runtime(a).name.startswith("app-"))


if __name__ == "__main__":
    unittest.main()
