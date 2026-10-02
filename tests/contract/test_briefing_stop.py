"""End of a briefing (System-ADR 0021): no open point may stay only in the protocol."""
from datetime import date, timedelta

from harness import ContractTest, project, write

LATER = (date.today() + timedelta(days=5)).isoformat()


def protocol(p, zurueckgestellt="- keine"):
    return write(p / ".keel" / "work" / "briefing" / f"{date.today().isoformat()}.md",
                 f"---\ntyp: briefing\ndatum: {date.today().isoformat()}\n---\n\n## Entscheidungen\n- x\n\n"
                 f"## Zurückgestellt\n{zurueckgestellt}\n")


class BriefingStopTest(ContractTest):
    def start(self, p, prompt="/keel:briefing"):
        r = self.hook("skill-gate", {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "session_id": "s1",
                                     "cwd": str(p), "transcript_path": ""}, proj=p)
        self.assertPassed(r)
        return self.runtime(p) / "state" / "briefing-s1.json"

    def stop(self, p):
        return self.hook("briefing-stop", {"hook_event_name": "Stop", "session_id": "s1", "cwd": str(p),
                                           "stop_hook_active": False}, proj=p)

    def assertStopBlocked(self, r, mentions):
        self.assertEqual(r.rc, 0, r)
        self.assertEqual((r.json or {}).get("decision"), "block", r)
        self.assertIn(mentions, r.json["reason"])

    def test_without_a_briefing_nothing_is_checked(self):
        p = project()
        protocol(p, zurueckgestellt="")
        self.assertPassed(self.stop(p))

    def test_start_without_a_due_briefing_leaves_no_marker(self):
        p = project()
        self.assertFalse(self.start(p, "/keel:start").exists())
        self.assertTrue(self.start(p).exists())

    def test_the_conversation_is_not_checked_before_a_protocol_exists(self):
        p = project("briefing")
        marker = self.start(p)
        r = self.stop(p)
        self.assertPassed(r)
        self.assertTrue(marker.exists())

    def test_missing_section_blocks(self):
        p = project()
        self.start(p)
        write(p / ".keel" / "work" / "briefing" / f"{date.today().isoformat()}.md",
              f"---\ntyp: briefing\ndatum: {date.today().isoformat()}\n---\n## Entscheidungen\n- x\n")
        self.assertStopBlocked(self.stop(p), "Zurückgestellt")

    def test_reference_to_a_missing_follow_up_blocks(self):
        p = project()
        self.start(p)
        protocol(p, "- Korridor: .keel/decisions/wiedervorlagen/gibt-es-nicht.md")
        self.assertStopBlocked(self.stop(p), "gibt-es-nicht.md gibt es nicht")

    def test_a_blocking_reason_left_open_blocks(self):
        p = project("briefing")
        self.start(p)
        protocol(p)
        self.assertStopBlocked(self.stop(p), "v-esk.md sperrt noch")

    def test_postponed_with_follow_up_and_reference_passes(self):
        p = project("briefing")
        marker = self.start(p)
        v = p / ".keel" / "decisions" / "pending" / "v-esk.md"
        v.write_text(v.read_text().replace("status: offen", "status: zurueckgestellt"))
        r = self.script("wiedervorlage.py", "neu", p, "--titel", "Esk", "--frage", "Jetzt?", "--quelle", "Briefing",
                        "--faellig", LATER, "--vorlage", "v-esk.md", proj=p)
        self.assertEqual(r.rc, 0, r)
        protocol(p, f"- v-esk: {r.out.strip()}")
        r = self.stop(p)
        self.assertPassed(r)
        self.assertFalse(marker.exists())
        self.assertIn("briefing_geprueft", [e.get("event") for e in r.events])

    def test_postponing_without_naming_it_in_the_section_blocks(self):
        p = project("briefing")
        self.start(p)
        v = p / ".keel" / "decisions" / "pending" / "v-esk.md"
        v.write_text(v.read_text().replace("status: offen", "status: zurueckgestellt"))
        self.script("wiedervorlage.py", "neu", p, "--titel", "Esk", "--frage", "Jetzt?", "--quelle", "Briefing",
                    "--faellig", LATER, "--vorlage", "v-esk.md", proj=p)
        protocol(p)
        self.assertStopBlocked(self.stop(p), "v-esk.md ist zurückgestellt")

    def test_lets_go_after_three_blocks_and_records_it(self):
        p = project()
        marker = self.start(p)
        protocol(p, "- ohne Verweis")
        for _ in range(3):
            self.assertStopBlocked(self.stop(p), "verweist auf keine Wiedervorlage")
        r = self.stop(p)
        self.assertPassed(r)
        self.assertFalse(marker.exists())
        self.assertIn("briefing_protokoll_offen", [e.get("event") for e in r.events])
