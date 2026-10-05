"""Missing permissions reach the human (System-ADR 0025): every PermissionRequest is recorded, and the next
briefing's agenda lists them grouped, without what a configured prefix already allows."""
from harness import ContractTest, project, write


def request(p, cmd, role="keel:entwickler"):
    payload = {"hook_event_name": "PermissionRequest", "tool_name": "Bash", "cwd": str(p), "session_id": "s1",
               "tool_input": {"command": cmd},
               "permission_suggestions": [{"type": "addRules", "behavior": "allow", "destination": "localSettings",
                                           "rules": [{"toolName": "Bash", "ruleContent": cmd.split()[0] + " " +
                                                      cmd.split()[1] + ":*"}]}]}
    if role:
        payload.update(agent_type=role, agent_id="a1")
    return payload


class MissingPermissionsTest(ContractTest):
    def agenda(self, p):
        r = self.script("briefing_needed.py", p, "--json", proj=p)
        self.assertIn(r.rc, (0, 1), r)
        return [i for i in r.json["tagesordnung"] if i["art"] == "fehlende-freigaben"]

    def test_a_request_is_recorded_and_never_answered(self):
        p = project()
        r = self.hook("freigabe", request(p, "pnpm vitest run tests/unit/a.test.ts"), proj=p)
        self.assertEqual((r.rc, r.json), (0, None), r)
        [e] = [e for e in r.events if e["event"] == "freigabe_fehlt"]
        self.assertEqual((e["role"], e["tool"], e["vorschlag"]), ("entwickler", "Bash", ["Bash(pnpm vitest:*)"]))

    def test_the_agenda_groups_them_and_drops_allowed_prefixes(self):
        p = project()
        for cmd in ("pnpm vitest run a", "pnpm vitest run b", "pnpm lint --fix"):
            self.hook("freigabe", request(p, cmd), proj=p)
        self.hook("freigabe", request(p, "cargo build", role=None), proj=p)
        [item] = self.agenda(p)
        self.assertEqual(item["befehle"], ["Bash: pnpm vitest", "Bash: pnpm lint", "Bash: cargo build"])
        self.assertIn("pnpm vitest (2×, entwickler)", item["grund"])
        self.assertIn("cargo build (1×, lead)", item["grund"])
        cfg = p / ".keel" / "config.yaml"
        cfg.write_text(cfg.read_text().replace("befehle: []", "befehle: [pnpm vitest, pnpm lint, cargo build]"))
        self.assertEqual(self.agenda(p), [])

    def test_a_briefing_closes_what_came_before(self):
        p = project()
        self.hook("freigabe", request(p, "pnpm vitest run a"), proj=p)
        write(p / ".keel" / "work" / "briefing" / "2099-01-01.md", "---\ntyp: briefing\ndatum: 2099-01-01\n---\n")
        self.assertEqual(self.agenda(p), [])
