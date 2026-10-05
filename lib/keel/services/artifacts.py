"""Checks on keel artifacts (handoff files with frontmatter) that gates and the command line share.

validate() returns the problems in the wording the hooks have always shown the roles, so a role reads the same
message whether the check runs in the dispatcher or through scripts/frontmatter.py validate.
"""
from keel.store import frontmatter


def _empty(value):
    return not value


def validate(path, typ=None, status=None, require=(), nonempty=()):
    """'' when the file passes, else '<path>: problem; problem'. A file without frontmatter is a problem too.
    status: allowed values (list or comma text). An unreadable file raises ReadError or ParseError: that is
    "cannot check", never "invalid"."""
    data, _ = frontmatter.load(path)
    if data is None:
        return f"{path}: no frontmatter found"
    if isinstance(status, str):
        status = status.split(",")
    errors = []
    if typ and data.get("typ") != typ:
        errors.append(f"typ is '{data.get('typ')}', expected '{typ}'")
    if status is not None and data.get("status") not in status:
        errors.append(f"status is '{data.get('status')}', expected one of {', '.join(status)}")
    for key in require:
        if key and key not in data:
            errors.append(f"missing field '{key}'")
    for key in nonempty:
        if key and _empty(data.get(key)):
            errors.append(f"field '{key}' is empty")
    return f"{path}: " + "; ".join(errors) if errors else ""
