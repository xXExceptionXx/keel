"""ADRs the project kept before keel (System-ADR 0024): keel numbers after them, and no role may change them."""
import subprocess

from harness import BASH, REPO, ContractTest, project, write

ADR = "---\nnummer: offen\ntitel: {t}\nstatus: Accepted (delegiert)\ndatum: 2026-10-05\nentscheider: PO\n---\n# x\n"


class ExternalAdrTest(ContractTest):
    def setUp(self):
        super().setUp()
        self.p = project()
        write(self.p / "docs" / "adr" / "0007-keine-vermittlung.md", "# 0007 – Keine Vermittlung\n")
        write(self.p / "docs" / "adr" / "TEMPLATE.md", "# Vorlage\n")
        cfg = self.p / ".keel" / "config.yaml"
        cfg.write_text(cfg.read_text().replace("weitere_ordner: []", "weitere_ordner: [docs/adr]"))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "keel")
        self.git("branch", "-M", "main")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.p), "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True,
                       capture_output=True)

    def test_new_adrs_are_numbered_after_the_project_folder(self):
        r = self.script("adr.py", "neu", self.p, "Rechte", proj=self.p)
        self.assertEqual((r.rc, r.out.strip()), (0, ".keel/adr/0008-rechte.md"), r)

    def test_drafts_get_numbers_after_the_project_folder_at_integration(self):
        self.git("switch", "-q", "-c", "feature/x")
        write(self.p / ".keel" / "adr" / "entwurf-cache.md", ADR.format(t="Cache"))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "x")
        self.git("switch", "-q", "main")
        self.git("merge", "--no-ff", "--no-commit", "feature/x")
        r = self.script("adr.py", "number", self.p, proj=self.p)
        self.assertEqual(r.rc, 0, r)
        self.assertIn("0008-cache.md", r.out)

    def stop(self, role):
        payload = {"hook_event_name": "SubagentStop", "agent_type": f"keel:{role}", "agent_id": "a1",
                   "cwd": str(self.p), "last_assistant_message": "fertig"}
        return self.hook("agent-stop", payload, proj=self.p)

    def test_no_role_changes_an_adr_of_the_project_folder(self):
        for role, change in (("architekt", "edit"), ("supervisor", "edit"), ("planer", "new")):
            with self.subTest(role=role, change=change):
                self.setUp()
                self.seed_agent(self.p, role=role, ref="2026-10-05")
                self.adr_snapshot(self.p)
                if change == "edit":
                    write(self.p / "docs" / "adr" / "0007-keine-vermittlung.md", "# 0007 – Doch Vermittlung\n")
                else:
                    write(self.p / "docs" / "adr" / "0008-neu.md", "# 0008 – Neu\n")
                r = self.stop(role)
                self.assertTrue(r.blocked, r)
                self.assertIn("ändert nur der Mensch", r.json["reason"])

    def test_doctor_reports_a_missing_folder(self):
        cfg = self.p / ".keel" / "config.yaml"
        cfg.write_text(cfg.read_text().replace("weitere_ordner: [docs/adr]", "weitere_ordner: [docs/adr, docs/fehlt]"))
        out = subprocess.run([BASH, str(REPO / "bin" / "keel"), "doctor", "--project", str(self.p)], capture_output=True,
                             text=True, env=self.env()).stdout
        self.assertIn("docs/fehlt", out)
