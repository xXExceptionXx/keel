"""The private denylist: patterns of names that must never leave this machine (System-ADR 0021).

It lives outside every repository: $KEEL_LEAK_DENYLIST (newline-separated, used by CI) or the file
~/.config/keel/leak-denylist ($KEEL_LEAK_DENYLIST_FILE overrides the path).
"""
import os
from pathlib import Path

from keel.domain.errors import ReadError
from keel.domain.leakpatterns import parse_denylist

DEFAULT = Path.home() / ".config" / "keel" / "leak-denylist"


def location():
    return Path(os.environ.get("KEEL_LEAK_DENYLIST_FILE") or DEFAULT)


def load():
    """Compiled patterns, or None when no denylist exists. Raises ReadError, re.error."""
    text = os.environ.get("KEEL_LEAK_DENYLIST")
    if text is None:
        path = location()
        if not path.is_file():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ReadError(f"{path} nicht lesbar: {exc}") from exc
    return parse_denylist(text)
