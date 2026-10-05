"""Two levels before the briefing (System-ADR 0021): blocking reasons stop the roles, the agenda never does."""
import subprocess
from datetime import date, timedelta

from harness import ContractTest, project, write

TODAY = date.today()


def day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


def followup(p, name, faellig="", vorlage="", runde=1, status="offen"):
    return write(p / ".keel" / "decisions" / "wiedervorlagen" / f"{name}.md",
                 f"---\ntyp: wiedervorlage\ntitel: {name}\nfrage: f?\nquelle: Briefing\nfaellig: {faellig}\n"
                 f"status: {status}\nvorlage: {vorlage}\nrunde: {runde}\n---\n")


def vorlage(p, name, **fields):
    head = "".join(f"{k}: {v}\n" for k, v in {"typ": "vorlage", "titel": name, "von": "PO", "datum": day(-5),
                                               "status": "offen", **fields}.items())
    return write(p / ".keel" / "decisions" / "pending" / f"{name}.md", f"---\n{head}---\n")


class AgendaTest(ContractTest):
    def needed(self, p, *extra):
        r = self.script("briefing_needed.py", p, "--json", *extra, proj=p)
        self.assertIn(r.rc, (0, 1), r)
        return r

    def arts(self, r, key):
        return [i["art"] for i in r.json[key]]

    def test_due_follow_up_is_on_the_agenda_and_blocks_nothing(self):
        p = project()
        followup(p, "faellig", faellig=day(0))
        followup(p, "terminlos")
        followup(p, "kuenftig", faellig=day(3))
        r = self.needed(p)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(sorted(i["titel"] for i in r.json["tagesordnung"] if i["art"] == "wiedervorlage"),
                         ["faellig", "terminlos"])
        due = self.script("due.py", p, "--json", proj=p)
        self.assertFalse(due.json["hart"], due)
        self.assertIn("tagesordnung", [i["art"] for i in due.json["faellig"]])

    def test_unreadable_follow_up_is_an_agenda_item_not_an_error(self):
        p = project()
        write(p / ".keel" / "decisions" / "wiedervorlagen" / "kaputt.md", "---\ntitel: [offen\n---\n")
        r = self.needed(p)
        self.assertEqual(r.rc, 0, r)
        self.assertIn("wiedervorlage-unlesbar", self.arts(r, "tagesordnung"))

    def test_follow_up_far_past_its_date_blocks(self):
        p = project()
        followup(p, "alt", faellig=day(-8))
        r = self.needed(p)
        self.assertEqual(r.rc, 1, r)
        self.assertEqual(self.arts(r, "gruende"), ["wiedervorlage-ueberfaellig"])

    def test_postponed_vorlage_comes_back_and_blocks_the_second_time(self):
        p = project()
        vorlage(p, "v-zurueck", status="zurueckgestellt", eskaliert="Supervisor")
        followup(p, "runde1", faellig=day(3), vorlage="v-zurueck.md")
        self.assertEqual(self.needed(p).rc, 0)  # postponed and not due: neither blocks nor shows
        followup(p, "runde1", faellig=day(0), vorlage="v-zurueck.md")
        r = self.needed(p)
        self.assertEqual(r.rc, 0, r)
        self.assertIn("zurueckgestellt", self.arts(r, "tagesordnung"))
        followup(p, "runde1", faellig=day(0), vorlage="v-zurueck.md", runde=2)
        r = self.needed(p)
        self.assertEqual(r.rc, 1, r)
        self.assertEqual(self.arts(r, "gruende"), ["zurueckgestellt-faellig"])

    def test_postponed_vorlage_without_follow_up_blocks(self):
        p = project()
        vorlage(p, "v-verwaist", status="zurueckgestellt", eskaliert="Supervisor")
        r = self.needed(p)
        self.assertEqual(r.rc, 1, r)
        self.assertEqual(self.arts(r, "gruende"), ["zurueckgestellt-ohne-wiedervorlage"])

    def test_motor_proposal_of_the_coach_does_not_block_a_project_one_does(self):
        p = project()
        vorlage(p, "v-motor", von="Coach", ebene="motor")
        r = self.needed(p)
        self.assertEqual(r.rc, 0, r)
        self.assertIn("motor-vorschlag", self.arts(r, "tagesordnung"))
        vorlage(p, "v-projekt", von="Coach", ebene="projekt")
        self.assertEqual(self.arts(self.needed(p), "gruende"), ["coach-vorlage"])

    def test_passed_on_proposal_returns_after_30_days_unless_decided(self):
        p = project()
        write(p / ".keel" / "decisions" / "done" / "v-alt.md",
              f"---\ntyp: vorlage\ntitel: alt\nvon: Coach\nebene: motor\nstatus: weitergereicht\n"
              f"motor_vorschlag: 2026-08-01-x-abc\nweitergereicht: {day(-31)}\n---\n")
        write(p / ".keel" / "decisions" / "done" / "v-neu.md",
              f"---\ntyp: vorlage\ntitel: neu\nstatus: weitergereicht\nmotor_vorschlag: y\nweitergereicht: {day(-5)}\n---\n")
        r = self.needed(p)
        self.assertEqual([i["titel"] for i in r.json["tagesordnung"] if i["art"] == "motor-weitergereicht"], ["alt"])
        write(self.metrics / "motor" / "2026-08-01-x-abc.md", "---\ntyp: motorvorschlag\nstatus: umgesetzt\n---\n")
        self.assertNotIn("motor-weitergereicht", self.arts(self.needed(p), "tagesordnung"))

    def test_audit_items_waiting_more_than_two_days(self):
        p = project()
        write(p / ".keel" / "backlog.md",
              "# Backlog\n\n## vorgeschlagen\n\n"
              f"- [BL-1] Alt\n  Herkunft: Audit\n  Datum: {day(-3)}\n"
              f"- [BL-2] Frisch\n  Herkunft: Audit\n  Datum: {day(-1)}\n"
              "- [BL-3] Ohne Datum\n  Herkunft: Audit\n"
              f"- [BL-4] Kein Audit\n  Herkunft: Mensch\n  Datum: {day(-9)}\n\n## bereit\n")
        r = self.needed(p)
        self.assertEqual(sorted(i["titel"] for i in r.json["tagesordnung"] if i["art"] == "audit-backlog"),
                         ["BL-1 Alt", "BL-3 Ohne Datum"])

    def test_proposed_adr_on_the_base_branch_while_a_feature_is_checked_out(self):
        p = project()
        write(p / ".keel" / "adr" / "0004-cache.md", "---\nnummer: 0004\ntitel: Cache\nstatus: Proposed\n---\n")
        git = ["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["add", ".keel/adr/0004-cache.md"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "adr"], check=True)
        subprocess.run(git + ["switch", "-q", "-c", "feature/x"], check=True)
        r = self.needed(p)
        self.assertEqual(r.rc, 0, r)
        items = [i for i in r.json["tagesordnung"] if i["art"] == "proposed-adr"]
        self.assertEqual([i["datei"] for i in items], [".keel/adr/0004-cache.md"])

    def test_the_adr_template_is_never_on_the_agenda(self):
        p = project()
        r = self.needed(p)
        self.assertNotIn("0000-vorlage", str(r.json))


class FollowupMetricsTest(ContractTest):
    def figures(self, p):
        r = self.script("metrics.py", p, "--json", proj=p)
        self.assertIn(r.rc, (0, 3), r)
        return {k["kennzahl"]: k["wert"] for k in r.json["kennzahlen"]}

    def test_follow_ups_and_passed_on_vorlagen_leave_the_escalation_figures_alone(self):
        p = project("briefing")
        before = self.figures(p)
        followup(p, "eins", faellig=day(2))
        followup(p, "zwei")
        write(p / ".keel" / "decisions" / "done" / "v-motor.md",
              f"---\ntyp: vorlage\ntitel: M\nvon: Coach\nebene: motor\ndatum: {day(-3)}\nstatus: weitergereicht\n---\n")
        after = self.figures(p)
        for key in ("vorlagen_pro_woche", "eskalationsquote_prozent"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(after["offene_wiedervorlagen"], 2)
