"""Direction of the layers in lib/keel (System-ADR 0020), read from the imports with ast; standard library only."""
import ast
import importlib.util
import json
import sys
import sysconfig
import unittest
from pathlib import Path

from tests.unit.base import REPO

import keel

LAYERS = ["domain", "store", "integrations", "services", "interfaces"]
PACKAGE = REPO / "lib" / "keel"


def module_of(path):
    rel = path.relative_to(PACKAGE.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return parts


def imports(path):
    """(line, absolute module name) of every import in a file; relative imports resolved."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    here = module_of(path)
    package = here if path.name == "__init__.py" else here[:-1]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - node.level + 1]
                name = ".".join(base + ([node.module] if node.module else []))
            else:
                name = node.module
            out.append((node.lineno, name))
            out += [(node.lineno, f"{name}.{a.name}") for a in node.names if name == "keel"]
    return out


def layer_of(parts):
    return parts[1] if len(parts) > 1 and parts[1] in LAYERS else None


def is_stdlib(name):
    top = name.split(".")[0]
    if top in sys.builtin_module_names:
        return True
    spec = importlib.util.find_spec(top)
    if spec is None or spec.origin in (None, "built-in", "frozen"):
        return spec is not None
    stdlib = Path(sysconfig.get_paths()["stdlib"]).resolve()
    origin = Path(spec.origin).resolve()
    return stdlib in origin.parents and "site-packages" not in origin.parts


def violations(entries):
    """entries: (label, module parts, imports). Every import of a higher layer."""
    wrong = []
    for label, parts, found in entries:
        own = layer_of(parts)
        for line, name in found:
            target = layer_of(name.split("."))
            if name.split(".")[0] != "keel" or own is None or target is None:
                continue  # the package root (version) is free for everyone
            if LAYERS.index(target) > LAYERS.index(own):
                wrong.append(f"{label}:{line}: {own} importiert {name}")
    return wrong


class ArchitectureTest(unittest.TestCase):
    def files(self):
        return sorted(PACKAGE.rglob("*.py"))

    def test_layers_import_only_downwards(self):
        self.assertEqual(violations((f.relative_to(REPO), module_of(f), imports(f)) for f in self.files()), [])

    def test_checker_finds_an_upward_import(self):
        found = violations([("x.py", ["keel", "store", "x"], [(3, "keel.services.doctor"), (4, "keel.domain.errors")])])
        self.assertEqual(found, ["x.py:3: store importiert keel.services.doctor"])

    def test_domain_has_no_input_or_output(self):
        for f in (PACKAGE / "domain").rglob("*.py"):
            for line, name in imports(f):
                self.assertFalse(name.split(".")[0] in ("os", "pathlib", "subprocess", "io", "shutil") or
                                 name.startswith("keel.store"), f"{f}:{line}: {name}")

    def test_standard_library_only(self):
        foreign = [f"{f.relative_to(REPO)}:{line}: {name}" for f in self.files() for line, name in imports(f)
                   if name.split(".")[0] != "keel" and not is_stdlib(name)]
        self.assertEqual(foreign, [])

    def test_version_matches_the_plugin(self):
        for manifest in ("plugin.json", "marketplace.json"):
            data = json.loads((REPO / ".claude-plugin" / manifest).read_text(encoding="utf-8"))
            versions = [data.get("version")] + [p.get("version") for p in data.get("plugins", [])]
            self.assertIn(keel.__version__, versions, manifest)


if __name__ == "__main__":
    unittest.main()
