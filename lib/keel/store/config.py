"""Project configuration .keel/config.yaml: schema with defaults in one place, read with the codec.

Values from the file are text. get() falls back to the schema default when the file has no value.
A test keeps SCHEMA and templates/keel/config.yaml in step.
"""
import re

from keel.domain.errors import ReadError
from keel.store import codec
from keel.store.paths import Paths

ROLES = ("architekt", "auditor", "coach", "entwickler", "lead", "planer", "po", "reviewer", "supervisor", "tester")
BUDGET_KEYS = ("tool_calls", "diff_lines", "minutes")

SCHEMA = {
    "git": {"base_branch": "main", "feature_prefix": "feature/", "fix_prefix": "fix/"},
    "test": {"command": "npm test --silent", "acceptance": "npm test --silent", "timeout": 480},
    "budget": {
        "tool_calls": 60, "diff_lines": 300, "minutes": 30,
        "architekt_tool_calls": 200, "architekt_minutes": 60,
        "auditor_tool_calls": 150, "auditor_minutes": 45,
        "coach_tool_calls": 150, "coach_minutes": 45,
        "po_tool_calls": 100, "planer_tool_calls": 100,
        "context_tokens": 100000,
    },
    "korridore": {
        "vorlagen_pro_woche": "2-5",
        "entscheidungsdauer_tage": "0-2",
        "gekippte_delegierte_adrs_prozent": "0-10",
        "gekippte_supervisor_entscheidungen_prozent": "0-15",
        "eskalationsquote_prozent": "10-40",
        "einwaende_bei_abweichung_prozent": "50-100",
        "review_runden_pro_aufgabe": "1-2",
        "ruecklaufquote_review_prozent": "0-30",
        "fix_befunde_prozent": "0-20",
        "pflege_verfallen_prozent": "0-50",
        "neuschnitt_quote_prozent": "0-20",
        "blockierte_uebergaben_prozent": "0-20",
        "budget_verstoesse": "0-0",
        "kontext_alarme": "0-0",
        "audit_abweichungen_pro_bericht": "0-3",
        "diff_zeilen_pro_aufgabe": "20-300",
        "tokens_pro_aufgabe_k": "0-400",
    },
    "review": {"schwelle_blockierend": 0, "schwelle_wichtig": 0, "max_runden": 4},
    "pflege": {"max_aufgaben_pro_runde": 2, "verfall_tage": 42},
    "supervisor": {"model": "claude-fable-5-1"},
    "adr": {"weitere_ordner": []},
    "monitor": {"autostart": False, "port": 8765},
    "faelligkeiten": {
        "coach_tage": 30, "coach_min_rollenlaeufe": 40, "coach_nach_modellwechsel_rollenlaeufe": 10,
        "architektur_tage": 7, "architektur_min_commits": 10, "wiedervorlage_ueberfaellig_tage": 7,
    },
    "compliance": {"pii_patterns": ""},
    "backlog": {
        "provider": "markdown",
        "github": {
            "repo": "",
            "label_prefix": "keel:",
            "labels": {"vorgeschlagen": "", "bereit": "", "in_arbeit": "", "erledigt": "", "verworfen": ""},
        },
    },
}

# Keys the template leaves out (commented example); the schema knows them anyway.
OPTIONAL = {"backlog.github"}
CHOICES = {"backlog.provider": ("markdown", "github")}
CORRIDOR = re.compile(r"^\s*\d+(\.\d+)?\s*-\s*\d+(\.\d+)?\s*$")


def text(value):
    """A schema default as the file would hold it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def default(key):
    node = SCHEMA
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node if isinstance(node, (dict, list)) else text(node)


def load_file(path):
    """The tree of a config file; {} when it does not exist. Raises ReadError or ParseError."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadError(f"{path} nicht lesbar: {exc}") from exc
    return codec.loads(text, source=str(path))


def load(project):
    return load_file(Paths(project).config)


def lookup(tree, key):
    """The value at a dotted key, or None."""
    node = tree
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def get(tree, key, fallback=None):
    """File value, else the schema default, else fallback."""
    value = lookup(tree, key)
    if value is None or value == "":
        value = default(key)
    return fallback if value is None else value


def get_int(tree, key, fallback=None):
    """An integer setting; the schema default (or fallback) when the value is missing or not a whole number."""
    for value in (lookup(tree, key), default(key), fallback):
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def section(tree, name):
    """A section of the file merged over its schema defaults (text values)."""
    out = {k: (v if isinstance(v, (dict, list)) else text(v)) for k, v in (SCHEMA.get(name) or {}).items()}
    got = tree.get(name)
    if isinstance(got, dict):
        out.update(got)
    return out


def validate(tree):
    """Messages about the tree against the schema: unknown keys, wrong kinds, numbers, corridors."""
    out = []
    _walk(tree, SCHEMA, "", out)
    return out


def _walk(node, schema, prefix, out):
    for key, value in node.items():
        path = f"{prefix}{key}"
        if key not in schema:
            if not _role_budget(prefix, key):
                out.append(f"{path}: unbekannter Schlüssel")
            elif not _is_int(value):
                out.append(f"{path}: '{value}' ist keine ganze Zahl")
            continue
        expected = schema[key]
        if isinstance(expected, dict):
            if value == "":
                continue
            if not isinstance(value, dict):
                out.append(f"{path}: erwartet einen Abschnitt mit Schlüsseln")
            else:
                _walk(value, expected, path + ".", out)
            continue
        if isinstance(expected, list):
            if not isinstance(value, list) and value != "":
                out.append(f"{path}: erwartet eine Liste, etwa [docs/adr]")
            continue
        if isinstance(value, (dict, list)):
            out.append(f"{path}: erwartet einen einzelnen Wert")
        elif isinstance(expected, bool):
            if value.lower() not in ("true", "false", "ja", "nein", "yes", "no", "1", "0"):
                out.append(f"{path}: '{value}' ist kein Wahrheitswert (true oder false)")
        elif isinstance(expected, int):
            if not _is_int(value):
                out.append(f"{path}: '{value}' ist keine ganze Zahl")
        elif prefix == "korridore." and not CORRIDOR.match(value):
            out.append(f"{path}: '{value}' hat nicht die Form min-max")
        elif path in CHOICES and value not in CHOICES[path]:
            out.append(f"{path}: '{value}' ist keiner von {', '.join(CHOICES[path])}")


def _role_budget(prefix, key):
    if prefix != "budget.":
        return False
    return any(key == f"{r}_{k}" for r in ROLES for k in BUDGET_KEYS)


def _is_int(value):
    return isinstance(value, str) and value.strip().isdigit()
