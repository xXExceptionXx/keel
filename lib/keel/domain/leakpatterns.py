"""Patterns of text that must not leave a project or enter the public repository (System-ADR 0021).

Shared by scripts/compliance_scan.py (secrets in a task's diff), tests/leak_check.py (commits of keel itself) and
`keel motor add` (a proposal that leaves the project for the machine-wide inbox). Only reasons are reported, never
the matched text.
"""
import re

SECRETS = [
    (r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "private key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}\b", "GitHub token"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "API secret key"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack token"),
    (r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]", "hard-coded credential"),
]
NOREPLY_EMAIL = re.compile(r"^(\d+\+)?[A-Za-z0-9-]+@users\.noreply\.github\.com$|^noreply@(github|anthropic)\.com$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EXAMPLE_EMAIL = re.compile(r"@(example\.(com|org|net)|users\.noreply\.github\.com)$|^noreply@(github|anthropic)\.com$")
HOME_PATH = re.compile(
    r"(?:/Users|/home)/(?!(?:x|user|username|name|me|runner|you|<[^>]*>|\$\w+|\$\{\w+\})(?:/|\b))[A-Za-z0-9._-]+")
ALLOW_MARKER = "leak-check: allow"


def parse_denylist(text):
    """Compiled patterns from a denylist text: one regex per line, case-insensitive, # starts a comment line.
    Raises re.error for a broken pattern."""
    patterns = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line, re.IGNORECASE))
    return patterns


def scan(text, denylist=(), extra=()):
    """Reasons a text would leak: secrets, home paths, foreign email addresses, denylist entries and extra
    (pattern, label) pairs. A line with the allow marker is skipped."""
    found = []
    for line in str(text or "").splitlines() or [""]:
        if ALLOW_MARKER in line:
            continue
        for pattern, label in list(SECRETS) + list(extra):
            if re.search(pattern, line) and label not in found:
                found.append(label)
        if HOME_PATH.search(line) and "home path" not in found:
            found.append("home path")
        if any(not EXAMPLE_EMAIL.search(m) for m in EMAIL.findall(line)) and "email address" not in found:
            found.append("email address")
        for i, pattern in enumerate(denylist):
            label = f"denylist entry {i + 1}"
            if pattern.search(line) and label not in found:
                found.append(label)
    return found
