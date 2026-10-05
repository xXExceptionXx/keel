"""interfaces.hooks: the error contract of the dispatcher (System-ADR 0019, 0022) with stand-in steps."""
import io
import json
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout

from tests.unit.base import TempTest
from keel.interfaces import hooks
from keel.services.hooks.base import CannotCheck, Context, Refuse
from keel.store import events
from keel.store.paths import Paths


def module(name, fn):
    mod = types.ModuleType(f"keel.services.hooks.{name}")
    mod.run = fn
    sys.modules[mod.__name__] = mod
    return name


class DispatcherTest(TempTest):
    def setUp(self):
        super().setUp()
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        self.saved = dict(hooks.STEPS)

    def tearDown(self):
        hooks.STEPS.clear()
        hooks.STEPS.update(self.saved)
        for name in list(sys.modules):
            if name.startswith("keel.services.hooks._t_"):
                del sys.modules[name]
        super().tearDown()

    def steps(self, *steps):
        hooks.STEPS["PreToolUse"] = [(name, kind, hooks._any, module(f"_t_{name}", fn)) for name, kind, fn in steps]

    def call(self, payload=None):
        out, err = io.StringIO(), io.StringIO()
        raw = json.dumps(payload or {"cwd": str(self.proj), "tool_name": "Read"})
        with redirect_stdout(out), redirect_stderr(err):
            rc = hooks.run("pre-tool-use", raw=raw)
        return rc, json.loads(out.getvalue()) if out.getvalue() else None, err.getvalue()

    def events(self):
        return events.read(Paths(self.proj).events).events

    def test_first_refusal_wins_and_every_step_runs(self):
        ran = []
        self.steps(("a", hooks.GATE, lambda h: ran.append("a") or Refuse("erst")),
                   ("b", hooks.GATE, lambda h: ran.append("b") or Refuse("dann")),
                   ("c", hooks.OBSERVER, lambda h: ran.append("c")))
        rc, answer, _ = self.call()
        self.assertEqual(rc, 0)
        self.assertEqual(ran, ["a", "b", "c"])
        self.assertEqual(answer["hookSpecificOutput"]["permissionDecisionReason"], "erst")

    def test_a_gate_that_cannot_check_blocks(self):
        def fail(h):
            raise CannotCheck("Datei unlesbar")
        self.steps(("g", hooks.GATE, fail))
        rc, answer, err = self.call()
        self.assertEqual((rc, answer), (2, None))
        self.assertIn("g konnte nicht prüfen (Datei unlesbar)", err)

    def test_a_crashing_gate_blocks(self):
        self.steps(("g", hooks.GATE, lambda h: 1 / 0))
        rc, _, err = self.call()
        self.assertEqual(rc, 2)
        self.assertIn("brach unerwartet ab (ZeroDivisionError", err)

    def test_a_crashing_observer_is_recorded_and_lets_go(self):
        self.steps(("o", hooks.OBSERVER, lambda h: 1 / 0), ("g", hooks.GATE, lambda h: Context("Hinweis")))
        rc, answer, _ = self.call()
        self.assertEqual(rc, 0)
        self.assertEqual(answer["hookSpecificOutput"]["additionalContext"], "Hinweis")
        self.assertEqual([(e["event"], e["hook"]) for e in self.events()], [("hook_error", "o")])

    def test_a_broken_payload_blocks_a_gate(self):
        self.steps(("g", hooks.GATE, lambda h: None))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = hooks.run("pre-tool-use", raw="{kaputt")
        self.assertEqual(rc, 2)
        self.assertIn("kein JSON-Objekt", err.getvalue())

    def test_the_third_internal_failure_at_an_agent_end_pulls_the_brake(self):
        def stop(h):
            h.agent_id, h.role = "a1", "tester"
            raise CannotCheck("kaputt")
        hooks.STEPS["SubagentStop"] = [("agent-stop", hooks.GATE, hooks._any, module("_t_stop", stop))]
        raw = json.dumps({"cwd": str(self.proj)})
        codes = []
        for _ in range(3):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                codes.append(hooks.run("subagent-stop", raw=raw))
        self.assertEqual(codes, [2, 2, 0])
        self.assertTrue(Paths(self.proj).brake.exists())

    def test_only_runs_one_step(self):
        ran = []
        self.steps(("a", hooks.GATE, lambda h: ran.append("a")), ("b", hooks.GATE, lambda h: ran.append("b")))
        with redirect_stdout(io.StringIO()):
            hooks.run(None, only="b", raw=json.dumps({"cwd": str(self.proj), "hook_event_name": "PreToolUse"}))
        self.assertEqual(ran, ["b"])


if __name__ == "__main__":
    unittest.main()
