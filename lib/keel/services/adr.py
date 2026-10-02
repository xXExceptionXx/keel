"""ADRs of a project (System-ADR 0021): level check at a role's end, drafts on branches, numbers at integration."""
import hashlib
import os
from datetime import date
from pathlib import Path

from keel.domain import adr
from keel.domain.errors import KeelError
from keel.integrations import git
from keel.store import frontmatter, io

ADR_DIR = Path(".keel") / "adr"
REWRITE_SUFFIXES = (".md", ".yaml", ".yml")


def _adr_dir(project):
    return Path(project) / ADR_DIR


def _names(project):
    d = _adr_dir(project)
    return adr.select(os.listdir(d)) if d.is_dir() else []


def _entry(path):
    raw = path.read_bytes()
    entry = {"sha256": hashlib.sha256(raw).hexdigest()}
    try:
        f = frontmatter.fields(path)
    except KeelError:
        entry["unlesbar"] = True
        return entry
    entry["entscheider"] = str(f.get("entscheider") or "")
    entry["status"] = str(f.get("status") or "")
    return entry


def snapshot(project):
    """State of every ADR: content hash, decider and status (or unreadable), plus the branch."""
    try:
        branch, base = git.current_branch(project), git.base(project)
    except KeelError:
        branch, base = "", ""
    return {"version": 1, "branch": branch, "basis": base,
            "adrs": {n: _entry(_adr_dir(project) / n) for n in _names(project)}}


def compare(project, before, role):
    """Problems of the ADR changes a role made since the snapshot `before` (System-ADR 0021, part D)."""
    after = snapshot(project)
    old, new = before.get("adrs", {}), after["adrs"]
    on_base = bool(after["branch"]) and after["branch"] == after["basis"]
    problems = []
    for name in sorted(set(old) | set(new)):
        a, b = old.get(name), new.get(name)
        if a is not None and b is not None and a["sha256"] == b["sha256"]:
            continue
        if b is not None and b.get("unlesbar"):
            problems.append(f"{ADR_DIR / name}: Frontmatter unlesbar, reparieren")
            continue
        fields_before = None if a is None or a.get("unlesbar") else a
        problems += adr.check_change(role, name, fields_before, b)
        if a is None and not on_base and not adr.is_draft(name):
            problems.append(f"{ADR_DIR / name}: auf einem Feature-Branch entstehen ADRs als Entwurf ohne Nummer; "
                            f"Pfad mit `adr.py neu <projekt> <slug>` holen")
    return problems


def new_path(project, slug, titel=None):
    """Create a new ADR from the template rules and return its path: numbered on the base branch, a draft
    (entwurf-<slug>.md, nummer: offen) on any other branch."""
    slug = adr.slugify(slug)
    on_base = git.on_base(project)
    if on_base:
        number = max([adr.number_of(n) or 0 for n in _names(project)] + [0]) + 1
        name, nummer, heading = adr.numbered_name(number, slug), f"{number:04d}", f"{number:04d}"
    else:
        name, nummer, heading = adr.draft_name(slug), "offen", "Entwurf"
    path = _adr_dir(project) / name
    titel = titel or slug.replace("-", " ")
    text = (f"---\nnummer: {nummer}\ntitel: {titel}\nstatus: Proposed\ndatum: {date.today().isoformat()}\n"
            f"entscheider: offen\nsupersedes:\n---\n\n# {heading}: {titel}\n\n## Kontext\n\n## Optionen\n\n"
            f"## Entscheidung\n\n## Folgen\n")
    if not io.create_exclusive(path, text):
        raise KeelError(f"{path.relative_to(project)} gibt es schon")
    return path


def check_integration(project, branch):
    """Problems that stop the integration of branch: a Proposed ADR it adds or changes, a numbered ADR it adds,
    uncommitted ADR changes when it is checked out. Raises KeelError when git cannot tell."""
    base = git.base(project)
    if not git.ref_exists(project, branch):
        raise KeelError(f"Branch {branch} gibt es nicht")
    since = git.merge_base(project, base, branch)
    added = set(git.diff_names(project, since, branch, str(ADR_DIR), diff_filter="A"))
    problems = []
    for rel in git.diff_names(project, since, branch, str(ADR_DIR), diff_filter="AM"):
        name = Path(rel).name
        if not adr.is_adr_name(name):
            continue
        data, _ = frontmatter.parse(git.show(project, branch, rel) or "", source=f"{branch}:{rel}")
        if data and adr.is_proposed(data.get("status")):
            problems.append(f"{rel}: noch Proposed; vor der Integration entscheiden (Vorlage, Supervisor fragen)")
        if rel in added and not adr.is_draft(name):
            problems.append(f"{rel}: nummeriert auf dem Branch; als Entwurf anlegen (entwurf-<slug>.md)")
    if git.current_branch(project) == branch and git.dirty(project, str(ADR_DIR)):
        problems.append(f"{ADR_DIR}: uncommittete Änderungen; erst committen")
    return problems


def number(project, dry_run=False):
    """Give every draft on the base branch the next free number, rewrite references under .keel first, rename
    last; idempotent. Returns {draft name: numbered name}."""
    if not git.on_base(project):
        raise KeelError(f"Nummern nur auf der Basis ({git.base(project)}), nicht auf {git.current_branch(project)}")
    folder = _adr_dir(project)
    names = _names(project)
    drafts = [n for n in names if adr.is_draft(n)]
    if not drafts:
        return {}

    def order(n):
        return (str(frontmatter.fields(folder / n).get("datum") or ""), n)

    nxt = max([adr.number_of(n) or 0 for n in names] + [0]) + 1
    plan = {}
    for n in sorted(drafts, key=order):
        plan[n] = adr.numbered_name(nxt, adr.slug_of(n))
        nxt += 1
    if dry_run:
        return plan
    keel = Path(project) / ".keel"
    for path in sorted(keel.rglob("*")):
        if not path.is_file() or path.suffix not in REWRITE_SUFFIXES:
            continue
        text = frontmatter.read_text(path)
        new = text
        for draft, target in plan.items():
            num = adr.number_of(target)
            new = adr.rewrite_refs(new, adr.slug_of(draft), num)
            if path.name == draft:
                new = adr.number_draft_header(new, num)
        if new != text:
            io.atomic_write(path, new)
    for draft, target in plan.items():
        src, dst = folder / draft, folder / target
        if git.is_tracked(project, src):
            git.mv(project, src, dst)
        else:
            os.replace(src, dst)
    return plan
