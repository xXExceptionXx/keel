"""Reading handoff files in a gate, with the gate's error contract: a file that cannot be read means the gate
cannot check (CannotCheck), never "field empty" or "nothing found" (System-ADR 0019)."""
import re
from pathlib import Path

from keel.domain.errors import ParseError, ReadError
from keel.services import artifacts
from keel.services.hooks.base import CannotCheck
from keel.store import frontmatter


def get(path, key):
    """A field as text ('' when the file has no frontmatter or the key is missing); lists joined with ', '."""
    try:
        data, _ = frontmatter.load(path)
    except (ReadError, ParseError) as exc:
        raise CannotCheck(f"{path} nicht lesbar: {exc}") from exc
    if data is None:
        return ""
    value = data.get(key)
    if value is None:
        return ""
    if isinstance(value, dict):
        import json
        return json.dumps(value, ensure_ascii=False)
    return ", ".join(value) if isinstance(value, list) else str(value)


def items(text):
    """Words of a list field as get() gives it ('a, b' or 'a,b')."""
    return text.replace(",", " ").split()


def find(folder, **wanted):
    """First file under folder (recursive, *.md, sorted) whose fields all match, '' when none."""
    folder = Path(folder)
    for p in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        try:
            data = frontmatter.fields(p)
        except (ReadError, ParseError) as exc:
            raise CannotCheck(f"{folder} nicht lesbar: {exc}") from exc
        if all(str(data.get(k)) == v for k, v in wanted.items()):
            return str(p)
    return ""


def find_all(folder, **wanted):
    """Every matching file; raises ReadError or ParseError on an unreadable file."""
    folder = Path(folder)
    hits = []
    for p in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        data = frontmatter.fields(p)
        if all(str(data.get(k)) == v for k, v in wanted.items()):
            hits.append(str(p))
    return hits


def check(path, typ=None, status=None, require=(), nonempty=()):
    """'' when the file passes, else the problem; an unreadable or missing file is a problem too (the role
    must repair or write it)."""
    try:
        return artifacts.validate(path, typ=typ, status=status, require=require, nonempty=nonempty)
    except (ReadError, ParseError) as exc:
        return str(exc)


def _lines(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def has_line(path, prefix):
    """A line starting with prefix (grep -q "^prefix"); False for a missing file."""
    lines = _lines(path)
    return lines is not None and any(line.startswith(prefix) for line in lines)


def contains(path, text, ignore_case=False):
    """text anywhere in the file (grep -q / grep -qi); False for a missing file."""
    lines = _lines(path)
    if lines is None:
        return False
    if ignore_case:
        text = text.lower()
        return any(text in line.lower() for line in lines)
    return any(text in line for line in lines)


def count_lines(path, pattern):
    """Lines matching the regular expression (grep -cE)."""
    lines = _lines(path) or []
    rx = re.compile(pattern)
    return sum(1 for line in lines if rx.search(line))
