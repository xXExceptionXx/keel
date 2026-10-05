"""Motor inbox instead of public issues (System-ADR 0021, part I)."""
import json
import subprocess
from datetime import date

from harness import REPO, ContractTest, project, write

KEEL = str(REPO / "bin" / "keel")


class MotorTest(ContractTest):
    def keel(self, p, *args, stdin=""):
        env = self.env({"KEEL_LEAK_DENYLIST": "Geheimprojekt", "KEEL_LEAK_DENYLIST_FILE": str(self.tmp / "none")})
        return subprocess.run([KEEL, *args], input=stdin, capture_output=True, text=True, cwd=str(p), env=env)

    def add(self, p, text, titel="Korridor"):
        return self.keel(p, "motor", "add", "--project", str(p), "--typ", "motorvorschlag", "--titel", titel,
                         "--hypothese", "Korridor 0-10, erwartet: weniger Vorlagen", stdin=text)

    def test_a_clean_proposal_lands_in_the_machine_wide_inbox_with_the_project_key(self):
        p = project()
        r = self.add(p, "Problem: der Korridor verlangt Einwände ohne Anlass.")
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = self.metrics / "motor" / f"{r.stdout.strip()}.md"
        self.assertTrue(entry.is_file())
        text = entry.read_text()
        self.assertIn(f"projekt: {self.runtime(p).name}", text)
        self.assertIn("status: offen", text)
        rows = json.loads(self.keel(p, "motor", "list", "--json").stdout)
        self.assertEqual([r["titel"] for r in rows], ["Korridor"])

    def test_text_that_would_leak_is_refused_without_repeating_it(self):
        p = project()
        for text, reason in (("Log unter /Users/" + "anna/projekt", "home path"),
                             ("Kontakt: anna@" + "firma.test", "email address"),
                             ("aus dem Geheimprojekt", "denylist entry 1"),
                             ("key = AKIA" + "ABCDEFGHIJKLMNOP", "AWS access key")):
            with self.subTest(reason=reason):
                r = self.add(p, text)
                self.assertEqual(r.returncode, 1, r.stderr)
                self.assertIn(reason, r.stderr)
                self.assertNotIn("anna", r.stderr)
                self.assertNotIn("Geheimprojekt", r.stderr)
        self.assertFalse((self.metrics / "motor").exists() and list((self.metrics / "motor").glob("*.md")))

    def test_status_is_set_in_the_keel_repo(self):
        p = project()
        entry_id = self.add(p, "Problem: x.").stdout.strip()
        r = self.keel(p, "motor", "set", entry_id, "status=angenommen", "system_adr=0022")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("system_adr: 0022", self.keel(p, "motor", "show", entry_id).stdout)
        self.assertEqual(self.keel(p, "motor", "set", entry_id, "status=vielleicht").returncode, 2)
        self.assertEqual(self.keel(p, "motor", "set", entry_id, "projekt=anderes").returncode, 2)

    def test_a_passed_on_vorlage_blocks_nothing(self):
        p = project()
        write(p / ".keel" / "decisions" / "pending" / "v-motor.md",
              f"---\ntyp: vorlage\ntitel: M\nvon: Coach\nebene: motor\nstatus: weitergereicht\n"
              f"motor_vorschlag: x\nweitergereicht: {date.today().isoformat()}\n---\n")
        r = self.script("briefing_needed.py", p, "--json", proj=p)
        self.assertEqual(r.rc, 0, r)

    def test_coach_vorlage_without_level_refuses_the_coach_stop(self):
        p = project()
        write(p / ".keel" / "work" / "coach" / "c1.md",
              "---\ntyp: coachbericht\ndatum: 2026-10-02\nkennzahlen_verletzt: 0\nvorschlaege: 1\n---\n")
        write(p / ".keel" / "decisions" / "pending" / "2026-10-02-coach-x.md",
              "---\ntyp: vorlage\ntitel: X\nvon: Coach\nstatus: offen\nhypothese: h\n---\n")
        write(self.runtime(p) / "state" / "agent-a1.ref", "c1\n")
        self.adr_snapshot(p)
        payload = {"hook_event_name": "SubagentStop", "agent_type": "keel:coach", "agent_id": "a1", "cwd": str(p),
                   "last_assistant_message": "fertig"}
        r = self.hook("agent-stop", payload, proj=p)
        self.assertEqual((r.json or {}).get("decision"), "block", r)
        self.assertIn("ohne gültige ebene", r.json["reason"])

    def test_no_skill_or_role_files_public_issues_any_more(self):
        texts = [f.read_text(encoding="utf-8") for d in ("skills", "agents") for f in (REPO / d).rglob("*.md")]
        self.assertFalse([t for t in texts if "gh issue create" in t])
