"""Rules for ADRs of a project: names, levels, who may write what (System-ADR 0021).

On the base branch an ADR is numbered (`0007-auth.md`); on any other branch it is a draft without number
(`entwurf-auth.md`, `nummer: offen`) that gets its number when the branch is integrated, so two branches never
take the same number. The template `0000-vorlage.md` and `README.md` are no ADRs.
"""
import re

NUMBERED = re.compile(r"^(\d{4})-(.+)\.md$")
DRAFT = re.compile(r"^entwurf-(.+)\.md$")
NOT_ADRS = {"0000-vorlage.md", "README.md"}

SUPERVISOR = "Supervisor"
HUMAN = "Mensch"
PO = "PO"
FOREIGN = {SUPERVISOR, HUMAN}

WRONG_LEVEL = "Lege eine Vorlage an, statt ein ADR auf fremder Stufe zu schreiben."

# Levels a role may give an ADR it creates or changes. None: Proposed without a decider.
RIGHTS = {
    "planer": {None},
    "architekt": {None},
    "po": {None, PO},
    "supervisor": {None, PO, SUPERVISOR},
}


def is_adr_name(name):
    return name not in NOT_ADRS and bool(NUMBERED.match(name) or DRAFT.match(name))


def select(names):
    """The ADR file names among names, sorted."""
    return sorted(n for n in names if is_adr_name(n))


def is_draft(name):
    return bool(DRAFT.match(name))


def number_of(name):
    m = NUMBERED.match(name)
    return int(m.group(1)) if m else None


def slug_of(name):
    m = NUMBERED.match(name) or DRAFT.match(name)
    return m.group(2) if m else None


def numbered_name(number, slug):
    return f"{number:04d}-{slug}.md"


def draft_name(slug):
    return f"entwurf-{slug}.md"


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
               .replace("ß", "ss")).strip("-")
    return s[:60].strip("-") or "adr"


def level(entscheider):
    """Supervisor, Mensch, PO or None (empty, `offen`, a placeholder). The old template value `Ich` is Mensch."""
    word = str(entscheider or "").strip().split(" ")[0].strip("<>|").casefold()
    if word == "supervisor":
        return SUPERVISOR
    if word in ("mensch", "ich"):
        return HUMAN
    if word == "po":
        return PO
    return None


def is_proposed(status):
    return str(status or "").strip().startswith("Proposed")


def check_change(role, name, before, after):
    """Problems of one ADR change by a role; before/after are field dicts or None (new, deleted).

    Every role but the Supervisor keeps away from files on the Supervisor's or the human's level, before or after.
    Roles without rights may not touch ADRs at all.
    """
    if role == "supervisor":
        if after is not None and level(after.get("entscheider")) == HUMAN:
            return [f"{name}: entscheider Mensch schreibt nur das Briefing. {WRONG_LEVEL}"]
        return []
    levels = {level((d or {}).get("entscheider")) for d in (before, after) if d is not None}
    if levels & FOREIGN:
        return [f"{name}: {_describe(before)} → {_describe(after)}. {WRONG_LEVEL}"]
    allowed = RIGHTS.get(role)
    if allowed is None:
        return [f"{name}: Rolle {role} ändert keine ADRs ({_describe(before)} → {_describe(after)}). {WRONG_LEVEL}"]
    if after is None:
        return [f"{name}: ADRs werden nicht gelöscht, sondern abgelöst (Superseded by)."]
    lv = level(after.get("entscheider"))
    if lv not in allowed:
        return [f"{name}: entscheider {after.get('entscheider')} ist nicht die Stufe von {role}. {WRONG_LEVEL}"]
    if lv is None and not is_proposed(after.get("status")):
        return [f"{name}: ohne entscheider nur mit status Proposed (gefunden: {after.get('status')})."]
    return []


def _describe(fields):
    if fields is None:
        return "nicht vorhanden"
    return f"entscheider {fields.get('entscheider') or 'leer'}, status {fields.get('status') or 'leer'}"


def rewrite_refs(text, slug, number):
    """Replace references to the draft entwurf-<slug> by the number: path form first, then the bare id."""
    nnnn = f"{number:04d}"
    text = text.replace(f"entwurf-{slug}.md", numbered_name(number, slug))
    return re.sub(rf"\bentwurf-{re.escape(slug)}\b", nnnn, text)


def number_draft_header(text, number):
    """In the draft itself: `nummer: offen` and the heading `# Entwurf:` get the number."""
    nnnn = f"{number:04d}"
    text = re.sub(r"(?m)^nummer:\s*offen\s*$", f"nummer: {nnnn}", text, count=1)
    return re.sub(r"(?m)^# Entwurf:", f"# {nnnn}:", text, count=1)
