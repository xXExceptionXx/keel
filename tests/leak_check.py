"""Blocks commits that would publish private data: identities, private names, home paths, emails and secrets.

  python3 tests/leak_check.py --staged          # pre-commit: staged diff plus the identity about to commit
  python3 tests/leak_check.py --range A..B      # pre-push and CI: every commit in the range, diff and message
  python3 tests/leak_check.py --range "HEAD --not --remotes"   # any git log revision arguments

Checks:
  identity   author and committer email must be a noreply address; names must not hit the private denylist
  secrets    the SECRETS patterns of lib/keel/domain/leakpatterns.py
  home path  /Users/<name>/ or /home/<name>/ other than generic placeholders
  email      any address outside example domains and noreply addresses
  denylist   private patterns, one regex per line, case-insensitive. They never live in this repo: read from
             $KEEL_LEAK_DENYLIST (CI secret, newline-separated) or the file ~/.config/keel/leak-denylist
             ($KEEL_LEAK_DENYLIST_FILE overrides the path)

Only added lines and commit messages are checked. A line containing `leak-check: allow` is skipped.
Exit codes: 0 clean, 1 findings, 2 cannot check (System-ADR 0019).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "lib"))
from keel.domain.leakpatterns import ALLOW_MARKER, NOREPLY_EMAIL, scan  # noqa: E402
from keel.domain.errors import KeelError  # noqa: E402
from keel.store import denylist as private_denylist  # noqa: E402


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def scan_text(text, denylist):
    """Findings of one line or message: a list of short reasons, never the matched private text."""
    return scan(text, denylist or ())


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
        denylist = private_denylist.load()
        if denylist is None:
            print(f"leak-check: no private denylist (set KEEL_LEAK_DENYLIST or create {private_denylist.DEFAULT}); "
                  "checking the generic rules only", file=sys.stderr)
        found = check_staged(denylist) if args.staged else check_range(args.range, denylist)
    except (RuntimeError, OSError, re.error, KeelError) as e:
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
