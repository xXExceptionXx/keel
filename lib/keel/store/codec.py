"""A strict YAML subset for frontmatter and .keel/config.yaml (F7, System-ADR 0020).

Understood:
  key: value             keys of letters, digits, _ . -
  key:                   followed by deeper lines: a nested mapping or a block list; else empty text
    - item               block list, indented or at the same indent as its key
  key: [a, "b, c"]       inline list
  "text", 'text', text   double quotes with JSON escapes, single quotes with '' for ', plain text
  # comment              whole line, or after whitespace outside quotes

Values stay text; there is no conversion to numbers or booleans. Anything else (tabs, block scalars | and >,
flow mappings {}, anchors, tags, nested structures in lists, unexpected indentation) is a ParseError naming
the line. A key written twice takes the later value; a section written twice is merged.
"""
import json
import re

from keel.domain.errors import ParseError

KEY = re.compile(r"^([A-Za-z0-9_.-]+):(?:\s+(.*))?$")
ITEM = re.compile(r"^-(?:\s+(.*))?$")
SIMPLE = re.compile(r"[A-Za-z0-9_./#@:-]+")
RESERVED = {"true", "false", "null", "yes", "no", "~"}


class _Line:
    __slots__ = ("no", "indent", "text")

    def __init__(self, no, indent, text):
        self.no, self.indent, self.text = no, indent, text


def loads(text, source=None, first_line=1):
    """Parse text into a dict (insertion order = file order). Raises ParseError."""
    lines = _lines(text, source, first_line)
    if not lines:
        return {}
    if lines[0].indent != 0:
        raise ParseError("erste Zeile ist eingerückt", lines[0].no, source)
    value, i = _block(lines, 0, 0, source)
    if not isinstance(value, dict):
        raise ParseError("oberste Ebene muss aus Schlüsseln bestehen, nicht aus einer Liste", lines[0].no, source)
    if i != len(lines):
        raise ParseError("unerwartete Einrückung", lines[i].no, source)
    return value


def _lines(text, source, first_line):
    out = []
    for n, raw in enumerate(text.split("\n"), first_line):
        line = raw.rstrip()
        stripped = line.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("\t") or "\t" in line[: len(line) - len(stripped)]:
            raise ParseError("Tabulator in der Einrückung", n, source)
        out.append(_Line(n, len(line) - len(stripped), stripped))
    return out


def _block(lines, i, indent, source):
    """The mapping or list that starts at lines[i] with this indent; returns (value, next index)."""
    if ITEM.match(lines[i].text):
        return _list(lines, i, indent, source)
    return _mapping(lines, i, indent, source)


def _mapping(lines, i, indent, source):
    out = {}
    while i < len(lines) and lines[i].indent == indent:
        line = lines[i]
        m = KEY.match(line.text)
        if not m:
            if ITEM.match(line.text):
                raise ParseError("Listeneintrag ohne Schlüssel davor", line.no, source)
            raise ParseError(f"keine Zeile der Form 'schlüssel: wert': {line.text[:60]!r}", line.no, source)
        key, rest = m.group(1), (m.group(2) or "")
        i += 1
        value = scalar_or_list(rest, line.no, source)
        if value == "" and not _is_quoted_empty(rest):
            # empty: a nested block may follow, deeper, or a list at the same indent
            if i < len(lines) and lines[i].indent > indent:
                value, i = _block(lines, i, lines[i].indent, source)
            elif i < len(lines) and lines[i].indent == indent and ITEM.match(lines[i].text):
                value, i = _list(lines, i, indent, source)
        if i < len(lines) and lines[i].indent > indent:
            raise ParseError("unerwartete Einrückung", lines[i].no, source)
        if isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = merge(out[key], value)  # a section written twice: the later keys win
        else:
            out[key] = value
    return out, i


def merge(base, extra):
    out = dict(base)
    for k, v in extra.items():
        out[k] = merge(out[k], v) if isinstance(out.get(k), dict) and isinstance(v, dict) else v
    return out


def _list(lines, i, indent, source):
    out = []
    while i < len(lines) and lines[i].indent == indent and ITEM.match(lines[i].text):
        line = lines[i]
        rest = ITEM.match(line.text).group(1) or ""
        value = scalar_or_list(rest, line.no, source)
        if isinstance(value, list):
            raise ParseError("Listen in Listen werden nicht unterstützt", line.no, source)
        out.append(value)
        i += 1
        if i < len(lines) and lines[i].indent > indent:
            raise ParseError("verschachtelte Strukturen in Listen werden nicht unterstützt", lines[i].no, source)
    return out, i


def _is_quoted_empty(rest):
    r = strip_comment(rest)
    return r in ('""', "''")


def strip_comment(text):
    """text without a trailing comment: # at the start or after whitespace, outside quotes."""
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote == '"':
            if c == "\\":
                i += 2
                continue
            if c == '"':
                quote = None
        elif quote == "'":
            if c == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                quote = None
        elif c in "\"'" and (i == 0 or text[i - 1] in " \t[,"):
            quote = c
        elif c == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
        i += 1
    return text.strip()


def scalar_or_list(rest, line_no=None, source=None):
    """A value after 'key:' or '- ': text or an inline list."""
    value = strip_comment(rest).strip()
    if value.startswith("["):
        if not value.endswith("]"):
            raise ParseError("Liste ohne schließende Klammer", line_no, source)
        inner = value[1:-1].strip()
        return [scalar(p, line_no, source) for p in split_inline(inner, line_no, source)] if inner else []
    return scalar(value, line_no, source)


def split_inline(inner, line_no=None, source=None):
    parts, buf, quote, i = [], [], None, 0
    while i < len(inner):
        c = inner[i]
        if quote == '"' and c == "\\" and i + 1 < len(inner):
            buf.append(inner[i:i + 2])
            i += 2
            continue
        if quote:
            if c == quote:
                if quote == "'" and i + 1 < len(inner) and inner[i + 1] == "'":
                    buf.append("''")
                    i += 2
                    continue
                quote = None
        elif c in "\"'" and not "".join(buf).strip():
            quote = c
        elif c == ",":
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        elif c in "[]{}":
            raise ParseError(f"'{c}' in einer Liste wird nicht unterstützt", line_no, source)
        buf.append(c)
        i += 1
    if quote:
        raise ParseError("Anführungszeichen nicht geschlossen", line_no, source)
    parts.append("".join(buf).strip())
    if any(p == "" for p in parts):
        raise ParseError("leerer Eintrag in einer Liste", line_no, source)
    return parts


def scalar(value, line_no=None, source=None):
    value = value.strip()
    if not value:
        return ""
    head = value[0]
    if head == '"':
        end = _closing_double(value)
        if end is None:
            raise ParseError("Anführungszeichen nicht geschlossen", line_no, source)
        if end != len(value) - 1:
            raise ParseError("Text nach dem schließenden Anführungszeichen", line_no, source)
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1]  # an escape JSON does not know, e.g. C:\pfad: keep the text as written
    if head == "'":
        if len(value) < 2 or value[-1] != "'" or re.search(r"(?<!')'(?!')", value[1:-1].replace("''", "")):
            raise ParseError("einfache Anführungszeichen nicht sauber geschlossen", line_no, source)
        return value[1:-1].replace("''", "'")
    if head in "{":
        raise ParseError("Abbildungen in geschweiften Klammern werden nicht unterstützt", line_no, source)
    if head in "|>" and value.rstrip("+-0123456789") in ("|", ">"):
        raise ParseError("mehrzeilige Blöcke (| und >) werden nicht unterstützt", line_no, source)
    if head in "&*!":
        raise ParseError("Anker, Verweise und Tags werden nicht unterstützt", line_no, source)
    return value


def _closing_double(value):
    i = 1
    while i < len(value):
        if value[i] == "\\":
            i += 2
            continue
        if value[i] == '"':
            return i
        i += 1
    return None


def dump_scalar(value):
    """A text value as it is written: plain when that reads back the same, else as a JSON string."""
    v = str(value)
    if v == "" or re.search(r"[:#\[\]{}\"\\]|^['\s|>&*!]|\s$", v) or v.lower() in RESERVED:
        return json.dumps(v, ensure_ascii=False)
    return v


def dump_inline_list(values):
    """Inline form `[a, b]` when every item is simple, else None."""
    if all(SIMPLE.fullmatch(v or "") and not v.startswith(("#", "-", "@")) for v in values):
        return "[" + ", ".join(values) + "]"
    return None


def dumps(data, indent=0):
    """Mapping to text in the same subset; loads(dumps(x)) == x."""
    pad = " " * indent
    out = []
    for key, value in data.items():
        if isinstance(value, dict):
            if value:
                out.append(f"{pad}{key}:")
                out.append(dumps(value, indent + 2).rstrip("\n"))
            else:
                raise ValueError(f"leere Abbildung unter {key} lässt sich nicht schreiben")
        elif isinstance(value, list):
            if not value:
                out.append(f"{pad}{key}: []")
            else:
                inline = dump_inline_list([str(v) for v in value])
                if inline is not None:
                    out.append(f"{pad}{key}: {inline}")
                else:
                    out.append(f"{pad}{key}:")
                    out.extend(f"{pad}  - {dump_scalar(v)}" for v in value)
        else:
            out.append(f"{pad}{key}: {dump_scalar(value)}")
    return "\n".join(out) + "\n" if out else ""
