"""What the next briefing must decide (blocking) and what it should look at (agenda), System-ADR 0021.

Blocking reasons stop all roles until the briefing; they are read strictly, an unreadable file is an error (exit 2,
System-ADR 0019). The agenda never blocks; it is read tolerantly, an unreadable file becomes an agenda item.
"""
import os
from datetime import date

from keel.domain import adr, followup
from keel.domain.errors import KeelError
from keel.integrations import git
from keel.store import config, frontmatter
from keel.store.paths import motor_dir

POSTPONED = "zurueckgestellt"
PASSED_ON = "weitergereicht"
AUDIT_DAYS = 2
MOTOR_RETURN_DAYS = 30
MOTOR_FINAL = ("angenommen", "abgelehnt", "umgesetzt")


def _item(art, project, path, titel, **extra):
    out = {"art": art, "datei": str(path.relative_to(project)) if path is not None else "", "titel": titel or ""}
    out.update({k: v for k, v in extra.items() if v not in (None, "")})
    return out


def _md(folder):
    return sorted(p for p in folder.glob("*.md")) if folder.is_dir() else []


def _as_date(value):
    try:
        return followup.parse_date(value)
    except ValueError:
        return None


def followups(project):
    """(path, fields or None) of every follow-up file; None when it cannot be read."""
    folder = project / ".keel" / "decisions" / "wiedervorlagen"
    out = []
    for p in _md(folder):
        f = frontmatter.fields_tolerant(p)
        out.append((p, f if f and not followup.validate(f) else None))
    return out


def collect(project, today=None, backlog_items=None):
    """{"gruende": [...], "tagesordnung": [...]} for a project. backlog_items: list of backlog dicts or an
    exception text (str) when the backlog could not be read; None skips the backlog."""
    today = today or date.today()
    keel = project / ".keel"
    cfg = config.load_file(keel / "config.yaml")
    overdue_limit = config.get_int(cfg, "faelligkeiten.wiedervorlage_ueberfaellig_tage")
    blocking, agenda = [], []

    # supervisor decisions not yet presented
    adr_dir = keel / "adr"
    if adr_dir.is_dir():
        for name in adr.select(os.listdir(adr_dir)):
            d = frontmatter.fields(adr_dir / name)
            if adr.level(d.get("entscheider")) == adr.SUPERVISOR and str(d.get("vorgelegt", "")).lower() == "offen":
                blocking.append(_item("supervisor-entscheidung", project, adr_dir / name, d.get("titel")))

    fus = followups(project)
    open_for = {}
    for p, f in fus:
        if f is not None and followup.is_open(f) and f.get("vorlage"):
            open_for.setdefault(str(f["vorlage"]).strip(), (p, f))

    # Vorlagen
    handled = set()
    for p in _md(keel / "decisions" / "pending"):
        d = frontmatter.fields(p)
        status = d.get("status")
        if status == PASSED_ON:
            continue
        if status == POSTPONED:
            fu = open_for.get(p.name) or open_for.get(p.stem)
            if fu is None:
                blocking.append(_item("zurueckgestellt-ohne-wiedervorlage", project, p, d.get("titel"),
                                      grund="zurückgestellt, aber keine offene Wiedervorlage verweist darauf"))
                continue
            handled.add(fu[0])
            fp, ff = fu
            if followup.is_due(ff, today):
                if followup.round_of(ff) == 2 or followup.days_overdue(ff, today) > overdue_limit:
                    blocking.append(_item("zurueckgestellt-faellig", project, p, d.get("titel"),
                                          faellig=ff.get("faellig"), wiedervorlage=str(fp.relative_to(project))))
                else:
                    agenda.append(_item("zurueckgestellt", project, p, d.get("titel"), faellig=ff.get("faellig"),
                                        wiedervorlage=str(fp.relative_to(project))))
            continue
        if d.get("eskaliert") == "Supervisor":
            blocking.append(_item("richtungsweisend", project, p, d.get("titel")))
        elif d.get("von") == "Coach":
            if d.get("ebene") == "motor":
                agenda.append(_item("motor-vorschlag", project, p, d.get("titel"),
                                    grund="weiterreichen oder verwerfen"))
            else:
                blocking.append(_item("coach-vorlage", project, p, d.get("titel")))

    # follow-ups of their own
    for p, f in fus:
        if p in handled:
            continue
        if f is None:
            agenda.append(_item("wiedervorlage-unlesbar", project, p, p.stem, grund="Frontmatter reparieren"))
            continue
        if not followup.is_due(f, today):
            continue
        if followup.days_overdue(f, today) > overdue_limit:
            blocking.append(_item("wiedervorlage-ueberfaellig", project, p, f.get("titel"), faellig=f.get("faellig"),
                                  grund=f"{followup.days_overdue(f, today)} Tage über dem Termin"))
        else:
            agenda.append(_item("wiedervorlage", project, p, f.get("titel"), faellig=f.get("faellig"),
                                frage=f.get("frage")))

    # epics in course correction
    for p in _md(keel / "work" / "epics"):
        if p.name.endswith(".bewertung.md"):
            continue
        d = frontmatter.fields(p)
        if d.get("status") == "kurskorrektur":
            blocking.append(_item("kurskorrektur", project, p, d.get("titel")))

    agenda += _audit_backlog(backlog_items, today)
    agenda += _proposed_on_base(project)
    agenda += _motor_returning(project, today)
    return {"gruende": blocking, "tagesordnung": agenda}


def _audit_backlog(items, today):
    if items is None:
        return []
    if isinstance(items, str):
        return [{"art": "backlog-unlesbar", "datei": "", "titel": "Backlog nicht lesbar", "grund": items}]
    out = []
    for it in items:
        if str(it.get("herkunft", "")).strip().lower() != "audit" or it.get("status") != "vorgeschlagen":
            continue
        d = _as_date(it.get("datum"))
        if d is None:
            out.append({"art": "audit-backlog", "datei": "", "titel": f"{it.get('id')} {it.get('titel', '')}",
                        "grund": "Audit-Vorschlag, Datum unbekannt: bereit oder verworfen?"})
        elif (today - d).days > AUDIT_DAYS:
            out.append({"art": "audit-backlog", "datei": "", "titel": f"{it.get('id')} {it.get('titel', '')}",
                        "grund": f"seit {(today - d).days} Tagen vorgeschlagen: bereit oder verworfen?"})
    return out


def _proposed_on_base(project):
    """ADRs with status Proposed on the base branch: from the working tree on base, else from git objects."""
    try:
        base = git.base(project)
        if git.current_branch(project) == base:
            folder = project / ".keel" / "adr"
            names = adr.select(os.listdir(folder)) if folder.is_dir() else []
            texts = {n: frontmatter.read_text(folder / n) for n in names}
        else:
            names = adr.select(git.ls_tree(project, base, ".keel/adr"))
            texts = {n: git.show(project, base, f".keel/adr/{n}") or "" for n in names}
    except KeelError:
        return []
    out = []
    for name, text in texts.items():
        try:
            data, _ = frontmatter.parse(text, source=name)
        except KeelError:
            continue
        if data and adr.is_proposed(data.get("status")):
            out.append({"art": "proposed-adr", "datei": f".keel/adr/{name}", "titel": data.get("titel", ""),
                        "grund": f"auf {base} noch Proposed: annehmen oder verwerfen"})
    return out


def _motor_returning(project, today):
    """Proposals passed on to the motor inbox more than 30 days ago that nobody has decided yet."""
    out = []
    for p in _md(project / ".keel" / "decisions" / "done"):
        d = frontmatter.fields_tolerant(p)
        if d.get("status") != PASSED_ON:
            continue
        since = _as_date(d.get("weitergereicht"))
        if since is None or (today - since).days <= MOTOR_RETURN_DAYS:
            continue
        entry = motor_dir() / f"{d.get('motor_vorschlag', '')}.md"
        state = frontmatter.fields_tolerant(entry).get("status") if entry.is_file() else None
        if state in MOTOR_FINAL:
            continue
        out.append(_item("motor-weitergereicht", project, p, d.get("titel"),
                         grund=f"seit {(today - since).days} Tagen weitergereicht, im keel-Repo noch "
                               f"{state or 'ohne Eintrag'}"))
    return out
