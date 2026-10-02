"""The machine-wide motor inbox (System-ADR 0021): proposals of the Coach and findings of /keel:hilfe that concern
the plugin itself leave the project for ~/.keel-metrics/motor/, never for a public issue tracker.

An entry names its project only by the runtime key and holds no code. `add` refuses text that would leak
(secrets, home paths, foreign email addresses, the private denylist, the project's compliance.pii_patterns); it
names the reasons, never the matched text. A session in the keel repository reads the inbox and decides there.
"""
import re
from datetime import date

import keel
from keel.domain import adr as adr_rules
from keel.domain import leakpatterns
from keel.domain.errors import KeelError, Rejected, UsageError
from keel.store import config, denylist, frontmatter, io
from keel.store.paths import Paths, motor_dir

TYPES = ("motorvorschlag", "motorbefund")
STATUSES = ("offen", "angenommen", "abgelehnt", "umgesetzt")
SETTABLE = {"status", "system_adr", "entschieden", "notiz", "zusammengefuehrt_mit"}
ID = re.compile(r"^[A-Za-z0-9._-]+$")


def _pii(project):
    text = config.get(config.load(project), "compliance.pii_patterns") or ""
    return [(p.strip(), "compliance pattern") for p in str(text).split("|") if p.strip()]


def leaks(project, text):
    """Reasons the text must not leave the project; empty when it may."""
    return leakpatterns.scan(text, denylist.load() or (), _pii(project))


def add(project, typ, titel, body, hypothese="", kennzahlen="", quelle_vorlage=""):
    """Store a new entry and return its id. Raises Rejected when the text would leak."""
    if typ not in TYPES:
        raise UsageError(f"typ ist {' | '.join(TYPES)}")
    if not str(titel).strip() or not str(body).strip():
        raise UsageError("titel und Text sind Pflicht")
    found = leaks(project, "\n".join([titel, body, hypothese, kennzahlen, quelle_vorlage]))
    if found:
        raise Rejected("nicht abgelegt, der Text würde Projektinterna aus dem Projekt tragen: " + ", ".join(found)
                       + ". Umformulieren: Problem, Optionen, Empfehlung und Kennzahlen, ohne Code, Pfade, Namen.")
    paths = Paths(project)
    today = date.today().isoformat()
    data = {"typ": typ, "titel": titel, "datum": today, "projekt": paths.key, "plugin_version": keel.__version__,
            "quelle_vorlage": quelle_vorlage, "hypothese": hypothese, "kennzahlen": kennzahlen, "status": "offen",
            "system_adr": "", "entschieden": ""}
    text = frontmatter.render(data, f"\n# {titel}\n\n{body.strip()}\n")
    base = f"{today}-{paths.key}-{adr_rules.slugify(titel)}"
    for n in range(1, 100):
        entry_id = base if n == 1 else f"{base}-{n}"
        if io.create_exclusive(motor_dir() / f"{entry_id}.md", text):
            return entry_id
    raise KeelError(f"kein freier Name für {base}")


def _path(entry_id):
    if not ID.match(entry_id or ""):
        raise UsageError(f"ungültige ID {entry_id!r}")
    p = motor_dir() / f"{entry_id}.md"
    if not p.is_file():
        raise Rejected(f"kein Eintrag {entry_id} in {motor_dir()}")
    return p


def entries(status=None):
    out = []
    folder = motor_dir()
    for p in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        f = frontmatter.fields_tolerant(p)
        if not f:
            out.append({"id": p.stem, "unlesbar": True})
        elif status is None or f.get("status") == status:
            out.append({"id": p.stem, **{k: f.get(k, "") for k in
                        ("typ", "titel", "datum", "projekt", "plugin_version", "status", "system_adr")}})
    return out


def show(entry_id):
    return frontmatter.read_text(_path(entry_id))


def set_fields(entry_id, values):
    unknown = set(values) - SETTABLE
    if unknown:
        raise UsageError(f"nicht setzbar: {', '.join(sorted(unknown))}; erlaubt: {', '.join(sorted(SETTABLE))}")
    if "status" in values and values["status"] not in STATUSES:
        raise UsageError(f"status ist {' | '.join(STATUSES)}")
    frontmatter.update(_path(entry_id), values)
