"""keel doctor: is this project and this machine fit for keel? Shared by the command line, lage.py and /keel:hilfe.

Each check gives one finding: (pruefung, stufe ok|warnung|fehler, meldung).
"""
import shutil
import subprocess
import sys
import time
from typing import List, NamedTuple

from keel.domain.errors import ParseError, ReadError
from keel.store import config, events, frontmatter
from keel.store.paths import Paths

STALE_PENDING_SECONDS = 600
OK, WARNING, ERROR = "ok", "warnung", "fehler"


class Finding(NamedTuple):
    pruefung: str
    stufe: str
    meldung: str

    def as_dict(self):
        return self._asdict()


def run(project) -> List[Finding]:
    paths = Paths(project)
    return [
        check_python(),
        check_tool("git", "git fehlt im PATH; Review, Fälligkeiten und Compliance-Scan brauchen es"),
        check_tool("jq", "jq fehlt im PATH; ohne jq sperren die Gates jeden Aufruf (System-ADR 0019)"),
        check_config(paths),
        check_artifacts(paths),
        check_brake(paths),
        check_pending(paths),
        check_logs(paths),
    ]


def healthy(findings):
    return all(f.stufe == OK for f in findings)


def check_python():
    v = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info < (3, 9):
        return Finding("python", ERROR, f"Python {v}; keel braucht 3.9 oder neuer")
    return Finding("python", OK, f"Python {v}")


def check_tool(name, missing):
    path = shutil.which(name)
    if not path:
        return Finding(name, ERROR, missing)
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    return Finding(name, OK, (out.splitlines() or [path])[0])


def check_config(paths):
    if not paths.config.exists():
        return Finding("konfiguration", WARNING, f"{paths.config} fehlt; es gelten die Standardwerte")
    try:
        tree = config.load_file(paths.config)
    except (ReadError, ParseError) as exc:
        return Finding("konfiguration", ERROR, f"nicht lesbar: {exc}")
    problems = config.validate(tree)
    if problems:
        return Finding("konfiguration", WARNING, "; ".join(problems))
    return Finding("konfiguration", OK, "gültig")


def check_artifacts(paths):
    """Frontmatter of every Markdown file under .keel/. One the codec refuses stops due.py and with it every role
    (System-ADR 0019); this names the files so the human can fix them."""
    broken = []
    if paths.keel.is_dir():
        for p in sorted(paths.keel.rglob("*.md")):
            try:
                frontmatter.load(p)
            except (ReadError, ParseError) as exc:
                broken.append(str(exc).replace(str(paths.project) + "/", ""))
    if broken:
        return Finding("artefakte", ERROR, f"{len(broken)} Datei(en) nicht lesbar (sperren Rollen, wenn Fälligkeiten sie lesen): "
                       + "; ".join(broken[:10]) + (" …" if len(broken) > 10 else ""))
    return Finding("artefakte", OK, "alle Frontmatter lesbar")


def check_brake(paths):
    if paths.brake.exists():
        try:
            text = paths.brake.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            text = ""
        return Finding("notbremse", ERROR, f"alle Rollen gesperrt ({paths.brake}): {text}")
    return Finding("notbremse", OK, "nicht gezogen")


def check_pending(paths):
    now = time.time()
    stale = []
    if paths.state.exists():
        for p in sorted(paths.state.glob("pending-*")):
            try:
                age = now - p.stat().st_mtime
            except OSError:
                continue
            if age > STALE_PENDING_SECONDS:
                stale.append(f"{p.name} seit {int(age // 60)} Minuten")
    if stale:
        return Finding("pending", WARNING, "verwaiste Startmarken (Start abgebrochen?): " + ", ".join(stale)
                       + ". Aufräumen mit lage.py --clean")
    return Finding("pending", OK, "keine verwaisten Startmarken")


def check_logs(paths):
    broken = []
    for f in (paths.events, paths.hooklog):
        if f.exists():
            n = events.read(f).skipped
            if n:
                broken.append(f"{f.name}: {n} unlesbare Zeilen")
    if broken:
        return Finding("protokolle", WARNING, "; ".join(broken) + " (werden beim Lesen übersprungen)")
    return Finding("protokolle", OK, "lesbar")
