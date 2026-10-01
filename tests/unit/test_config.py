"""store.config: schema and template in step, lookups with defaults, validation."""
import unittest

from tests.unit.base import REPO
from keel.store import codec, config


def leaves(tree, prefix=""):
    out = {}
    for k, v in tree.items():
        if isinstance(v, dict):
            out.update(leaves(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.template = codec.loads((REPO / "templates" / "keel" / "config.yaml").read_text(encoding="utf-8"))

    def test_template_matches_schema(self):
        tpl = leaves(self.template)
        schema = {k: config.text(v) for k, v in leaves(config.SCHEMA).items()
                  if not any(k.startswith(o + ".") for o in config.OPTIONAL)}
        self.assertEqual(tpl, schema)

    def test_template_is_valid(self):
        self.assertEqual(config.validate(self.template), [])

    def test_lookup_falls_back_to_the_schema(self):
        tree = codec.loads("test:\n  timeout: 120\nreview:\n  max_runden: drei\n")
        self.assertEqual(config.get(tree, "test.timeout"), "120")
        self.assertEqual(config.get(tree, "test.command"), "npm test --silent")
        self.assertEqual(config.get_int(tree, "review.max_runden"), 4)
        self.assertEqual(config.get_int(tree, "test.timeout"), 120)
        self.assertEqual(config.get(tree, "gibt.es.nicht", "x"), "x")
        self.assertEqual(config.section(tree, "monitor"), {"autostart": "false", "port": "8765"})

    def test_validation_messages(self):
        tree = codec.loads("budget:\n  tool_calls: sechzig\n  tester_minutes: 9\n  fremd_minutes: 1\n"
                           "korridore:\n  kontext_alarme: viele\nmonitor:\n  autostart: vielleicht\n"
                           "backlog:\n  provider: jira\nunbekannt: 1\ngit: [a]\n")
        msgs = "\n".join(config.validate(tree))
        for part in ("budget.tool_calls: 'sechzig'", "budget.fremd_minutes: unbekannter", "kontext_alarme: 'viele'",
                     "autostart: 'vielleicht'", "provider: 'jira'", "unbekannt: unbekannter", "git: erwartet"):
            self.assertIn(part, msgs)
        self.assertNotIn("tester_minutes", msgs)


if __name__ == "__main__":
    unittest.main()
