"""Before a Vorhaben is discarded: open points that exist only on its branch are named (System-ADR 0021)."""
import json
import subprocess

from harness import ContractTest, project, write


class DiscardTest(ContractTest):
    def git(self, p, *args):
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True,
                       capture_output=True)

    def test_only_the_open_points_of_the_branch_are_listed(self):
        p = project()
        self.git(p, "add", "-A")
        self.git(p, "commit", "-q", "-m", "keel")
        self.git(p, "branch", "-M", "main")
        self.git(p, "switch", "-q", "-c", "feature/x")
        r = self.script("wiedervorlage.py", "neu", p, "--titel", "Nur hier", "--frage", "f?", "--quelle", "Lead",
                        proj=p)
        self.assertEqual(r.rc, 0, r)
        write(p / ".keel" / "decisions" / "pending" / "v-branch.md",
              "---\ntyp: vorlage\ntitel: Branch-Vorlage\nvon: PO\nstatus: offen\n---\n")
        write(p / ".keel" / "decisions" / "pending" / "v-fertig.md",
              "---\ntyp: vorlage\ntitel: Entschieden\nvon: PO\nstatus: entschieden\n---\n")
        self.git(p, "add", "-A")
        self.git(p, "commit", "-q", "-m", "work")
        r = self.script("wiedervorlage.py", "list", p, "--nur-branch", "feature/x", "--json", proj=p)
        self.assertEqual(r.rc, 1, r)
        self.assertEqual(sorted(x["titel"] for x in json.loads(r.out)), ["Branch-Vorlage", "Nur hier"])
        self.assertNotIn("v-offen", r.out)  # a Vorlage that is also on main is not the branch's own
        clean = self.script("wiedervorlage.py", "list", p, "--nur-branch", "main", proj=p)
        self.assertEqual(clean.rc, 0, clean)
