"""No script and no hook builds the runtime path or reads events, frontmatter or config on its own anymore:
everything goes through lib/keel (System-ADR 0020). Searches for the old patterns."""
import re
import unittest

from tests.unit.base import REPO

PATTERNS = {
    "metrics root built by hand": re.compile(r"\.keel-metrics|KEEL_METRICS_DIR"),
    "runtime folder from the folder name": re.compile(r"/\$\(basename \"\$\(?(p|proj|project|project_dir)\b"),
    "log file opened by name": re.compile(r"[\"'/](events|hooks)\.jsonl"),
    "own frontmatter reader": re.compile(r"^\s*def _?fm\(|^\s*def parse\(text", re.M),
    "own config reader": re.compile(r"^\s*def read\(path\)|split\(\"#\", 1\)", re.M),
    "import of the old modules": re.compile(r"^\s*from (frontmatter|config|jsonl) import", re.M),
    "sys.path trick": re.compile(r"sys\.path\.insert"),
}
ALLOWED = {("sys.path trick", "scripts/_keel.py")}


class LegacyPatternTest(unittest.TestCase):
    def files(self):
        return sorted(list((REPO / "scripts").glob("*.py")) + list((REPO / "scripts").glob("*.sh"))
                      + list((REPO / "hooks").glob("*.sh")))

    def test_no_old_patterns(self):
        found = []
        for f in self.files():
            rel = str(f.relative_to(REPO))
            text = f.read_text(encoding="utf-8")
            for name, pattern in PATTERNS.items():
                if (name, rel) in ALLOWED:
                    continue
                for m in pattern.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    found.append(f"{rel}:{line}: {name}: {m.group(0).strip()}")
        self.assertEqual(found, [])

    def test_patterns_still_match_the_old_code(self):
        old = {
            "metrics root built by hand": 'Path(os.environ.get("KEEL_METRICS_DIR", Path.home() / ".keel-metrics"))',
            "runtime folder from the folder name": 'd="$KEEL/$(basename "$p")/state"',
            "log file opened by name": 'metrics_dir / "events.jsonl"',
            "own frontmatter reader": "def fm(p):\n    pass",
            "own config reader": 'line = raw.split("#", 1)[0]',
            "import of the old modules": "from config import read as read_config",
            "sys.path trick": "sys.path.insert(0, str(Path(__file__).parent))",
        }
        for name, sample in old.items():
            self.assertRegex(sample, PATTERNS[name], name)


if __name__ == "__main__":
    unittest.main()
