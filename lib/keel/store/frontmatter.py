"""Frontmatter of keel artifacts: the header between two `---` lines, read and written with the codec.

parse/render keep the order of keys in data["__order__"] and leave the body untouched.
"""
from pathlib import Path

from keel.domain.errors import ParseError, ReadError
from keel.store import codec
from keel.store.io import atomic_write, file_lock

DELIM = "---"


def split(text):
    """(header, body, first header line number) or None when the text has no frontmatter."""
    if not text.startswith(DELIM + "\n"):
        return None
    end = text.find("\n" + DELIM + "\n", len(DELIM) + 1)
    if end < 0:
        stripped = text.rstrip("\n")
        if stripped.endswith("\n" + DELIM) or stripped == DELIM:
            end = len(stripped) - len(DELIM) - 1
        else:
            return None
    header = text[len(DELIM) + 1:end] if end > len(DELIM) else ""
    body = text[end + len(DELIM) + 2:]
    return header, body, 2


def parse(text, source=None):
    """(data with __order__, body), or (None, text) without frontmatter. Raises ParseError."""
    parts = split(text)
    if parts is None:
        return None, text
    header, body, first = parts
    data = codec.loads(header, source=source, first_line=first)
    data["__order__"] = [k for k in data]
    return data, body


def render(data, body):
    order = data.get("__order__", [k for k in data if k != "__order__"])
    keys = [k for k in order if k in data] + [k for k in data if k not in order and k != "__order__"]
    header = codec.dumps({k: data[k] for k in keys})
    return f"{DELIM}\n{header}{DELIM}\n{body}"


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadError(f"{path} nicht lesbar: {exc}") from exc


def load(path):
    """(data, body) of a file; data is None without frontmatter. Raises ReadError or ParseError."""
    return parse(read_text(path), source=str(path))


def fields(path):
    """The frontmatter fields of a file without __order__; {} without frontmatter. Raises ReadError, ParseError."""
    data, _ = load(path)
    return _clean(data)


def fields_tolerant(path):
    """Like fields(), but {} for a file that cannot be read or parsed. For reports, never for gates."""
    try:
        return fields(path)
    except (ReadError, ParseError):
        return {}


def load_tolerant(path):
    """(fields, body), or None when the file cannot be read or parsed."""
    try:
        data, body = load(path)
    except (ReadError, ParseError):
        return None
    return _clean(data), body


def _clean(data):
    return {k: v for k, v in (data or {}).items() if k != "__order__"}


def update(path, values):
    """Set fields in a file's frontmatter, under a lock and atomically. Raises ReadError or ParseError.

    A key the codec could not read back is refused, and the new text is parsed once more before it is written:
    the writer never leaves a file its own reader refuses.
    """
    for key in values:
        if not codec.KEY_NAME.fullmatch(str(key)):
            raise ParseError(f"ungültiger Schlüssel {key!r}: nur Buchstaben a-z, Ziffern und _ . -", source=str(path))
    with file_lock(path):
        data, body = load(path)
        if data is None:
            raise ParseError("keine Frontmatter", source=str(path))
        for key, value in values.items():
            data[key] = value
            if key not in data["__order__"]:
                data["__order__"].append(key)
        text = render(data, body)
        check, _ = parse(text, source=str(path))
        if {k: v for k, v in check.items() if k != "__order__"} != _clean(data):
            raise ParseError("neuer Inhalt liest sich nicht unverändert zurück; nichts geschrieben", source=str(path))
        atomic_write(path, text)
