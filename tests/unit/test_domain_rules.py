"""Pure rules of System-ADR 0021: ADR names and levels, follow-ups, leak patterns."""
import unittest
from datetime import date

from tests.unit.base import REPO  # noqa: F401  (puts lib on sys.path)
from keel.domain import adr, followup, leakpatterns


class AdrRulesTest(unittest.TestCase):
    def test_template_and_readme_are_no_adrs(self):
        self.assertEqual(adr.select(["0000-vorlage.md", "README.md", "0003-x.md", "entwurf-y.md", "notiz.md"]),
                         ["0003-x.md", "entwurf-y.md"])

    def test_slugs(self):
        self.assertEqual(adr.slug_of("0007-auth-flow.md"), "auth-flow")
        self.assertEqual(adr.slug_of("entwurf-cache.md"), "cache")
        self.assertIsNone(adr.slug_of("notiz.md"))

    def test_levels(self):
        self.assertEqual(adr.level("Supervisor"), adr.SUPERVISOR)
        self.assertEqual(adr.level("Ich"), adr.HUMAN)
        self.assertEqual(adr.level("<PO | Ich>"), adr.PO)
        self.assertIsNone(adr.level("offen"))
        self.assertIsNone(adr.level(None))

    def test_rights(self):
        proposed = {"status": "Proposed", "entscheider": "offen"}
        self.assertEqual(adr.check_change("planer", "a.md", None, proposed), [])
        self.assertEqual(adr.check_change("po", "a.md", None, {"status": "Accepted (delegiert)", "entscheider": "PO"}),
                         [])
        self.assertTrue(adr.check_change("planer", "a.md", None, {"status": "Accepted", "entscheider": "Supervisor"}))
        self.assertTrue(adr.check_change("entwickler", "a.md", None, proposed))
        human = {"status": "Accepted", "entscheider": "Mensch"}
        self.assertTrue(adr.check_change("po", "a.md", human, dict(human, status="Superseded by 0009")))
        self.assertEqual(adr.check_change("supervisor", "a.md", None, {"entscheider": "Supervisor"}), [])
        self.assertTrue(adr.check_change("supervisor", "a.md", None, {"entscheider": "Mensch"}))
        self.assertIn(adr.WRONG_LEVEL, adr.check_change("entwickler", "a.md", None, {"entscheider": "Supervisor"})[0])

    def test_rewrite_refs(self):
        text = "siehe adr/entwurf-auth.md und entwurf-auth, nicht entwurf-authx"
        self.assertEqual(adr.rewrite_refs(text, "auth", 24), "siehe adr/0024-auth.md und 0024, nicht entwurf-authx")
        self.assertEqual(adr.number_draft_header("nummer: offen\n---\n# Entwurf: Auth\n", 7),
                         "nummer: 0007\n---\n# 0007: Auth\n")


class FollowupTest(unittest.TestCase):
    def test_due_and_overdue(self):
        today = date(2026, 10, 10)
        self.assertTrue(followup.is_due({"status": "offen"}, today))
        self.assertTrue(followup.is_due({"status": "offen", "faellig": "2026-10-10"}, today))
        self.assertFalse(followup.is_due({"status": "offen", "faellig": "2026-10-11"}, today))
        self.assertFalse(followup.is_due({"status": "erledigt"}, today))
        self.assertEqual(followup.days_overdue({"status": "offen", "faellig": "2026-10-01"}, today), 9)

    def test_validate(self):
        ok = {"typ": "wiedervorlage", "titel": "t", "frage": "f", "quelle": "Briefing", "status": "offen"}
        self.assertEqual(followup.validate(ok), [])
        self.assertTrue(followup.validate(dict(ok, faellig="morgen")))
        self.assertTrue(followup.validate(dict(ok, runde="3")))
        self.assertTrue(followup.validate(dict(ok, status="vertagt")))


class LeakPatternsTest(unittest.TestCase):
    def test_reasons_never_contain_the_text(self):
        deny = leakpatterns.parse_denylist("# c\nGeheimprojekt\n")
        found = leakpatterns.scan("Geheimprojekt\n/Users/" + "anna/x\n" + "a@" + "mail.test", deny)
        self.assertEqual(sorted(found), ["denylist entry 1", "email address", "home path"])

    def test_placeholders_pass(self):
        self.assertEqual(leakpatterns.scan("/Users/x/p ci@example.com t@t /home/runner/w"), [])
