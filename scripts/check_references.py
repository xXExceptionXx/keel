#!/usr/bin/env python3
"""Check that every reference in a keel artifact exists: log file names, commit ids, file paths.

Usage: check_references.py <project-dir> <file.md> [<file.md> ...]
Prints one line per broken reference (file:line: kind: token) and a summary. Exit 1 if any is broken.

Existence, not truth: a commit id that resolves may still be described wrongly; that stays the Auditor's job.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

LOG = re.compile(r"\b([a-zA-Z0-9-]+-\d{8}T\d{6}Z\.log)\b")
COMMIT = re.compile(r"(?:`|\bCommit\s+|\bcommit\s+|\()([0-9a-f]{7,40})(?:`|\b)")
PATH = re.compile(r"`((?:\.keel|src|tests|docs|scripts|hooks|agents|skills|templates)/[A-Za-z0-9_./-]+|[A-Za-z0-9_./-]+\.(?:md|ts|js|py|json|yaml|yml|sh|toml|txt))`")
URL = re.compile(r"https?://\S+")


def commit_exists(project, sha):
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=project, capture_output=True).returncode == 0


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    metrics_logs = Path(os.environ.get("KEEL_METRICS_DIR", Path.home() / ".keel-metrics")) / project.name / "logs"
    broken = 0
    checked = 0
    for f in sys.argv[2:]:
        path = Path(f)
        if not path.is_absolute():
            path = project / path
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = URL.sub("", line)
            for name in LOG.findall(line):
                checked += 1
                if not ((project / ".keel" / "work" / "logs" / name).exists() or (metrics_logs / name).exists()):
                    print(f"{f}:{n}: log fehlt: {name}")
                    broken += 1
            for sha in COMMIT.findall(line):
                if not re.search(r"\d", sha) or not re.search(r"[a-f]", sha):
                    continue
                checked += 1
                if not commit_exists(project, sha):
                    print(f"{f}:{n}: commit unbekannt: {sha}")
                    broken += 1
            for p in PATH.findall(line):
                p = p.rstrip(".,;:")
                if "*" in p or "<" in p:
                    continue
                checked += 1
                if (project / p).exists() or (Path(__file__).resolve().parent.parent / p).exists():
                    continue  # project file, or a file of the keel plugin itself
                if "/" not in p and (any(project.rglob(p)) or any(Path(__file__).resolve().parent.parent.rglob(p))):
                    continue  # bare file name that exists somewhere in the project or the plugin
                print(f"{f}:{n}: pfad fehlt: {p}")
                broken += 1
    print(f"geprüft: {checked} Verweise, defekt: {broken}")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
