"""Blocks commits that would publish private data: identities, private names, home paths, emails and secrets.

  python3 tests/leak_check.py --staged          # pre-commit: staged diff plus the identity about to commit
  python3 tests/leak_check.py --range A..B      # pre-push and CI: every commit in the range, diff and message
  python3 tests/leak_check.py --range "HEAD --not --remotes"   # any git log revision arguments

Checks:
  identity   author and committer email must be a noreply address; names must not hit the private denylist
  secrets    the SECRETS patterns of scripts/compliance_scan.py
  home path  /Users/<name>/ or /home/<name>/ other than generic placeholders
  email      any address outside example domains and noreply addresses
  denylist   private patterns, one regex per line, case-insensitive. They never live in this repo: read from
             $KEEL_LEAK_DENYLIST (CI secret, newline-separated) or the file ~/.config/keel/leak-denylist
             ($KEEL_LEAK_DENYLIST_FILE overrides the path)

Only added lines and commit messages are checked. A line containing `leak-check: allow` is skipped.
Exit codes: 0 clean, 1 findings, 2 cannot check (System-ADR 0019).
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from compliance_scan import SECRETS  # noqa: E402

ALLOW_MARKER = "leak-check: allow"
NOREPLY_EMAIL = re.compile(r"^(\d+\+)?[A-Za-z0-9-]+@users\.noreply\.github\.com$|^noreply@(github|anthropic)\.com$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EXAMPLE_EMAIL = re.compile(r"@(example\.(com|org|net)|users\.noreply\.github\.com)$|^noreply@(github|anthropic)\.com$")
HOME_PATH = re.compile(r"(?:/Users|/home)/(?!(?:x|user|username|name|me|runner|you|<[^>]*>|\$\w+|\$\{\w+\})(?:/|\b))[A-Za-z0-9._-]+")
DEFAULT_DENYLIST = Path.home() / ".config" / "keel" / "leak-denylist"


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def load_denylist():
    """Private patterns from the environment or the local file; None when neither exists."""
    text = os.environ.get("KEEL_LEAK_DENYLIST")
    if text is None:
        path = Path(os.environ.get("KEEL_LEAK_DENYLIST_FILE") or DEFAULT_DENYLIST)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
    patterns = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line, re.IGNORECASE))
    return patterns


def scan_text(text, denylist):
    """Findings of one line or message: a list of short reasons, never the matched private text."""
    if ALLOW_MARKER in text:
        return []
    found = []
    for pattern, label in SECRETS:
        if re.search(pattern, text):
            found.append(label)
    if HOME_PATH.search(text):
        found.append("home path")
    if any(not EXAMPLE_EMAIL.search(m) for m in EMAIL.findall(text)):
        found.append("email address")
    for i, pattern in enumerate(denylist or []):
        if pattern.search(text):
            found.append(f"denylist entry {i + 1}")
    return found


def scan_identity(where, name, email, denylist):
    found = []
    if not NOREPLY_EMAIL.match(email):
        found.append(f"{where}: email is not a noreply address")
    if any(p.search(name) for p in denylist or []):
        found.append(f"{where}: name is on the denylist")
    return found


def scan_diff(diff, denylist, prefix=""):
    """Added lines of a unified diff with -U0."""
    found, path = [], "?"
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            for reason in scan_text(line[1:], denylist):
                found.append(f"{prefix}{path}: {reason}")
    return found


def ident(var):
    m = re.match(r"^(.*) <([^>]*)>", git("var", var).strip())
    return (m.group(1), m.group(2)) if m else ("", "")


def check_staged(denylist):
    found = []
    for var, where in (("GIT_AUTHOR_IDENT", "author"), ("GIT_COMMITTER_IDENT", "committer")):
        found += scan_identity(where, *ident(var), denylist)
    found += scan_diff(git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff"), denylist)
    return found


def check_range(rng, denylist):
    found = []
    log = git("log", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x1e", *rng.split())
    for entry in filter(str.strip, log.split("\x1e")):
        sha, an, ae, cn, ce, body = entry.strip("\n").split("\x00", 5)
        short = sha[:9]
        found += scan_identity(f"{short} author", an, ae, denylist)
        found += scan_identity(f"{short} committer", cn, ce, denylist)
        for line in body.splitlines():
            found += [f"{short} message: {r}" for r in scan_text(line, denylist)]
        found += scan_diff(git("show", "-U0", "--no-color", "--no-ext-diff", "--format=", sha), denylist, f"{short} ")
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--range", metavar="A..B")
    args = ap.parse_args()
    try:
        denylist = load_denylist()
        if denylist is None:
            print(f"leak-check: no private denylist (set KEEL_LEAK_DENYLIST or create {DEFAULT_DENYLIST}); "
                  "checking the generic rules only", file=sys.stderr)
        found = check_staged(denylist) if args.staged else check_range(args.range, denylist)
    except (RuntimeError, OSError, re.error) as e:
        print(f"leak-check: cannot check: {e}", file=sys.stderr)
        return 2
    if not found:
        return 0
    print("leak-check: blocked, this would publish private data:", file=sys.stderr)
    for f in dict.fromkeys(found):
        print(f"  {f}", file=sys.stderr)
    print("Fix the content, or the identity with your GitHub login and noreply address (GitHub settings, Emails):\n"
          "  git config user.name <login>\n  git config user.email <id>+<login>@users.noreply.github.com\n"
          f"A deliberate exception: add `{ALLOW_MARKER}` to the line.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
