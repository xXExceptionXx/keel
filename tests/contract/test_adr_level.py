"""ADRs only on the role's own level (System-ADR 0021, part D): the stop of a role that wrote one on a foreign
level is refused with a reason it can act on; a missing start state blocks."""
import subprocess

from harness import ContractTest, project, tool_call, write

WRONG = "fremder Stufe"


def adr(p, name, entscheider="", status="Proposed"):
    return write(p / ".keel" / "adr" / name,
                 f"---\nnummer: offen\ntitel: {name}\nstatus: {status}\nentscheider: {entscheider}\n---\n# x\n")


class AdrLevelTest(ContractTest):
    def stop(self, p, role):
        sd = self.runtime(p) / "state"
        write(sd / "agent-a1.ref", "T-x\n")
        payload = {"hook_event_name": "SubagentStop", "agent_type": f"keel:{role}", "agent_id": "a1", "cwd": str(p),
                   "last_assistant_message": "fertig"}
        return self.hook("agent-stop", payload, proj=p)

    def start(self, p):
        self.adr_snapshot(p)

    def reason(self, r):
        return (r.json or {}).get("reason", "") if r.rc == 0 else r.err

    def assertLevelRefused(self, r, mentions=WRONG):
        self.assertEqual(r.rc, 0, r)
        self.assertEqual((r.json or {}).get("decision"), "block", r)
        self.assertIn(mentions, r.json["reason"])

    def assertLevelPassed(self, r):
        self.assertNotIn("ADR auf fremder Stufe", self.reason(r), r)
        self.assertNotEqual(r.rc, 2, r)

    def test_working_role_writing_a_supervisor_adr_is_refused(self):
        p = project()
        self.start(p)
        adr(p, "entwurf-x.md", entscheider="Supervisor", status="Accepted (Supervisor)")
        r = self.stop(p, "entwickler")
        self.assertLevelRefused(r, "Lege eine Vorlage an, statt ein ADR auf fremder Stufe zu schreiben.")
        self.assertIn("entwurf-x.md", r.json["reason"])

    def test_planer_may_propose(self):
        p = project()
        self.start(p)
        adr(p, "entwurf-cache.md")
        self.assertLevelPassed(self.stop(p, "planer"))

    def test_planer_may_not_decide(self):
        p = project()
        self.start(p)
        adr(p, "entwurf-cache.md", entscheider="PO", status="Accepted (delegiert)")
        self.assertLevelRefused(self.stop(p, "planer"))

    def test_po_decides_on_its_level_but_never_touches_a_human_decision(self):
        p = project()
        adr(p, "0003-alt.md", entscheider="Mensch", status="Accepted")
        self.start(p)
        adr(p, "entwurf-neu.md", entscheider="PO", status="Accepted (delegiert)")
        self.assertLevelPassed(self.stop(p, "po"))
        self.start(p)
        adr(p, "0003-alt.md", entscheider="Mensch", status="Superseded by 0009")
        self.assertLevelRefused(self.stop(p, "po"))

    def test_supervisor_decides_but_never_for_the_human(self):
        p = project()
        self.start(p)
        adr(p, "entwurf-a.md", entscheider="Supervisor", status="Accepted (Supervisor)")
        self.assertLevelPassed(self.stop(p, "supervisor"))
        self.start(p)
        adr(p, "entwurf-b.md", entscheider="Mensch", status="Accepted")
        self.assertLevelRefused(self.stop(p, "supervisor"), "nur das Briefing")

    def test_numbered_adr_on_a_feature_branch_is_refused(self):
        p = project()
        subprocess.run(["git", "-C", str(p), "switch", "-q", "-c", "feature/x"], check=True)
        write(p / ".keel" / "config.yaml", (p / ".keel" / "config.yaml").read_text()
              + "\ngit:\n  base_branch: trunk\n")
        subprocess.run(["git", "-C", str(p), "branch", "trunk"], check=True)
        self.start(p)
        adr(p, "0005-cache.md")
        self.assertLevelRefused(self.stop(p, "planer"), "Entwurf ohne Nummer")

    def test_missing_start_state_blocks(self):
        p = project()
        r = self.stop(p, "entwickler")
        self.assertBlocked(r)
        self.assertIn("ADR-Stand", r.err)

    def test_agent_start_binds_the_state_to_the_agent(self):
        p = project()
        sd = self.runtime(p) / "state"
        write(sd / "adrstand-planer.json", "{}")
        r = self.hook("agent-start", {"hook_event_name": "SubagentStart", "agent_type": "keel:planer",
                                      "agent_id": "a7", "cwd": str(p)}, proj=p)
        self.assertEqual(r.rc, 0, r)
        self.assertTrue((sd / "agent-a7.adrstand.json").exists())
        self.assertFalse((sd / "adrstand-planer.json").exists())

    def test_an_adr_may_be_repaired_over_the_call_budget(self):
        p = project()
        sd = self.runtime(p) / "state"
        write(sd / "agent-a1.ref", "T-x\n")
        write(sd / "agent-a1.calls", "999\n")
        ok = self.hook("tool-gate", tool_call(p, "Edit", {"file_path": str(p / ".keel" / "adr" / "entwurf-x.md")},
                                              agent_type="keel:planer"), proj=p)
        self.assertPassed(ok)
        no = self.hook("tool-gate", tool_call(p, "Edit", {"file_path": str(p / "src" / "a.js")},
                                              agent_type="keel:planer"), proj=p)
        self.assertBlocked(no)
