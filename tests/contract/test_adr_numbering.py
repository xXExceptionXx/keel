"""ADR numbers at integration (System-ADR 0021, part F): drafts on branches, numbers only on the base branch."""
import json
import subprocess

from harness import ContractTest, project, write


def accepted(name, titel, datum="2026-10-01", extra=""):
    return (f"---\nnummer: offen\ntitel: {titel}\nstatus: Accepted (delegiert)\ndatum: {datum}\nentscheider: PO\n"
            f"{extra}---\n\n# Entwurf: {titel}\n")


class AdrNumberingTest(ContractTest):
    def setUp(self):
        super().setUp()
        self.p = project()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "keel")
        self.git("branch", "-M", "main")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.p), "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True,
                       capture_output=True)

    def adr(self, *args):
        return self.script("adr.py", *args, proj=self.p)

    def feature(self, name):
        self.git("switch", "-q", "-c", name, "main")

    def commit(self, msg="x"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def integrate(self, branch):
        self.git("switch", "-q", "main")
        self.git("merge", "--no-ff", "--no-commit", branch)
        r = self.adr("number", self.p)
        self.assertEqual(r.rc, 0, r)
        self.commit(f"Integrate {branch}")
        return json.loads(r.out)

    def test_new_adr_is_numbered_on_base_and_a_draft_on_a_branch(self):
        r = self.adr("neu", self.p, "Auth Flow")
        self.assertEqual((r.rc, r.out.strip()), (0, ".keel/adr/0001-auth-flow.md"), r)
        self.feature("feature/x")
        r = self.adr("neu", self.p, "cache", "--titel", "Cache")
        self.assertEqual(r.out.strip(), ".keel/adr/entwurf-cache.md", r)
        self.assertIn("nummer: offen", (self.p / ".keel" / "adr" / "entwurf-cache.md").read_text())

    def test_check_integration(self):
        self.feature("feature/x")
        self.adr("neu", self.p, "cache")
        self.commit()
        r = self.adr("check-integration", self.p, "--branch", "feature/x")
        self.assertEqual(r.rc, 1, r)
        self.assertIn("Proposed", r.out)
        write(self.p / ".keel" / "adr" / "entwurf-cache.md", accepted("entwurf-cache.md", "Cache"))
        self.commit()
        self.assertEqual(self.adr("check-integration", self.p, "--branch", "feature/x").rc, 0)
        self.assertEqual(self.adr("check-integration", self.p, "--branch", "feature/gibt-es-nicht").rc, 2)
        write(self.p / ".keel" / "adr" / "0007-roh.md", accepted("0007-roh.md", "Roh"))
        self.commit()
        r = self.adr("check-integration", self.p, "--branch", "feature/x")
        self.assertEqual(r.rc, 1, r)
        self.assertIn("nummeriert auf dem Branch", r.out)

    def test_number_rewrites_every_reference_and_is_idempotent(self):
        write(self.p / ".keel" / "adr" / "0003-alt.md",
              "---\nnummer: 0003\ntitel: Alt\nstatus: Accepted\nentscheider: Mensch\n---\n# 0003: Alt\n")
        self.commit()
        self.feature("feature/x")
        write(self.p / ".keel" / "adr" / "entwurf-cache.md", accepted("entwurf-cache.md", "Cache"))
        write(self.p / ".keel" / "adr" / "entwurf-neu.md",
              accepted("entwurf-neu.md", "Neu", datum="2026-10-02", extra="supersedes: entwurf-cache\n"))
        write(self.p / ".keel" / "work" / "plans" / "x.md",
              "---\ntyp: plan\nvorhaben: V1\nstatus: abgenommen\n---\nSiehe .keel/adr/entwurf-cache.md\n")
        write(self.p / ".keel" / "work" / "epics" / "e.md",
              "---\ntyp: epic\nstatus: aktiv\nleitentscheidungen: [entwurf-cache, 0003]\n---\n")
        write(self.p / ".keel" / "CLAUDE.md", (self.p / ".keel" / "CLAUDE.md").read_text()
              + "\n| entwurf-cache | Cache |\n")
        self.commit()
        plan = self.integrate("feature/x")
        self.assertEqual(plan, {"entwurf-cache.md": "0004-cache.md", "entwurf-neu.md": "0005-neu.md"})
        adr_dir = self.p / ".keel" / "adr"
        self.assertFalse(list(adr_dir.glob("entwurf-*.md")))
        cache = (adr_dir / "0004-cache.md").read_text()
        self.assertIn("nummer: 0004", cache)
        self.assertIn("# 0004: Cache", cache)
        self.assertIn("supersedes: 0004", (adr_dir / "0005-neu.md").read_text())
        self.assertIn(".keel/adr/0004-cache.md", (self.p / ".keel" / "work" / "plans" / "x.md").read_text())
        self.assertIn("[0004, 0003]", (self.p / ".keel" / "work" / "epics" / "e.md").read_text())
        self.assertIn("| 0004 | Cache |", (self.p / ".keel" / "CLAUDE.md").read_text())
        again = self.adr("number", self.p)
        self.assertEqual((again.rc, json.loads(again.out)), (0, {}))

    def test_two_branches_integrated_one_after_the_other_never_collide(self):
        self.feature("feature/a")
        write(self.p / ".keel" / "adr" / "entwurf-a.md", accepted("entwurf-a.md", "A"))
        self.commit()
        self.feature("feature/b")
        write(self.p / ".keel" / "adr" / "entwurf-b.md", accepted("entwurf-b.md", "B"))
        self.commit()
        self.assertEqual(self.integrate("feature/a"), {"entwurf-a.md": "0001-a.md"})
        self.assertEqual(self.integrate("feature/b"), {"entwurf-b.md": "0002-b.md"})

    def test_number_refuses_off_the_base_branch(self):
        self.feature("feature/x")
        r = self.adr("number", self.p)
        self.assertEqual(r.rc, 2, r)
        self.assertIn("nur auf der Basis", r.err)
