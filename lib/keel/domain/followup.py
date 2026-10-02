"""Wiedervorlagen (follow-ups): open points that come back on a date without blocking (System-ADR 0021).

A follow-up file lives in .keel/decisions/wiedervorlagen/<datum>-<slug>.md. One that carries `vorlage:` keeps a
postponed Vorlage alive: round 1 comes back on the agenda, round 2 blocks again, so nothing is put off forever.
"""
import re
from datetime import date

TYPE = "wiedervorlage"
STATUSES = ("offen", "erledigt")
REQUIRED = ("typ", "titel", "frage", "quelle", "status")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date(value):
    """A date from `YYYY-MM-DD`, or None for an empty value. Raises ValueError for anything else."""
    text = str(value or "").strip()
    if not text:
        return None
    if not DATE.match(text):
        raise ValueError(f"Datum {text!r} ist nicht YYYY-MM-DD")
    return date.fromisoformat(text)


def validate(fields):
    """Problems of a follow-up's fields; empty when it is well formed."""
    problems = [f"Feld {k} fehlt" for k in REQUIRED if not str(fields.get(k) or "").strip()]
    if fields.get("typ") and fields.get("typ") != TYPE:
        problems.append(f"typ ist {fields.get('typ')!r}, erwartet {TYPE}")
    if fields.get("status") and fields.get("status") not in STATUSES:
        problems.append(f"status {fields.get('status')!r} ist nicht {' | '.join(STATUSES)}")
    try:
        parse_date(fields.get("faellig"))
    except ValueError as exc:
        problems.append(f"faellig: {exc}")
    if str(fields.get("runde") or "1") not in ("1", "2"):
        problems.append("runde ist 1 oder 2")
    return problems


def is_open(fields):
    return fields.get("status") == "offen"


def due_date(fields):
    return parse_date(fields.get("faellig"))


def is_due(fields, today):
    """Open and either without date or on or after its date."""
    if not is_open(fields):
        return False
    d = due_date(fields)
    return d is None or d <= today


def days_overdue(fields, today):
    d = due_date(fields)
    return (today - d).days if d is not None and is_open(fields) else 0


def round_of(fields):
    return 2 if str(fields.get("runde") or "1") == "2" else 1
