#!/usr/bin/env python3
"""Deterministic compliance scan of a task's diff: secrets, new dependencies, personal-data patterns.

Usage: compliance_scan.py <project-dir> [--base <git-ref>] [--json]
Scans `git diff <base>` (default HEAD) plus untracked files, excluding .keel/ and lock files.

Result classes:
  block    secrets or private keys in the diff — the task may not finish
  vorlage  a new runtime or dev dependency — needs the human's decision (Befugnisse)
  pruefen  personal-data patterns, new external calls, logging of such fields — the Compliance agent judges
  frei     nothing found

Exit codes: 0 frei, 3 pruefen, 4 vorlage, 5 block. Patterns are extendable in .keel/config.yaml under compliance.*.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import read as read_config  # noqa: E402

SECRETS = [
    (r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "private key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}\b", "GitHub token"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "API secret key"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack token"),
    (r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]", "hard-coded credential"),
]
PII = [
    (r"(?i)\b(e-?mail|emailaddress|email_address)\b", "email address"),
    (r"(?i)\b(phone|telefon|mobile|handy)(number|_number|nummer)?\b", "phone number"),
    (r"(?i)\b(birth(date|day)|geburts(datum|tag)|date_of_birth|dob)\b", "date of birth"),
    (r"(?i)\b(iban|bic|kontonummer|account_number|credit_card|kreditkarte|card_number)\b", "bank or card data"),
    (r"(?i)\b(street|strasse|straße|postal_code|postleitzahl|zip_code|address|adresse)\b", "postal address"),
    (r"(?i)\b(ip_address|ipaddress|client_ip|remote_addr|x-forwarded-for)\b", "IP address"),
    (r"(?i)\b(first_name|last_name|full_name|vorname|nachname|surname)\b", "person name"),
    (r"(?i)\b(gender|geschlecht|religion|health|gesundheit|diagnos|ethnic|sexual)\b", "special category data"),
    (r"(?i)\b(geo|lat|lng|latitude|longitude|location|standort)\b", "location"),
]
EXTERNAL = [
    (r"(?i)\b(fetch|axios|got|request|http\.get|https\.get|urlopen|requests\.(get|post))\s*\(\s*['\"`]https?://([a-z0-9.-]+)", "external call"),
]
LOGGING = [
    (r"(?i)\b(console\.(log|info|warn|error)|logger\.|log\.(info|debug|warn|error)|print)\s*\(", "log statement"),
]
DEP_FILES = {
    "package.json": r'^\+\s*"([^"]+)"\s*:\s*"[^"]+"',
    "pyproject.toml": r'^\+\s*([A-Za-z0-9_.-]+)\s*[=>~<]',
    "requirements.txt": r"^\+\s*([A-Za-z0-9_.-]+)",
    "composer.json": r'^\+\s*"([^"]+)"\s*:\s*"[^"]+"',
    "go.mod": r"^\+\s*([a-z0-9./-]+)\s+v",
    "Cargo.toml": r'^\+\s*([A-Za-z0-9_-]+)\s*=',
    "Gemfile": r"^\+\s*gem\s+['\"]([^'\"]+)",
}
SCHEMA_HINT = re.compile(r"(?i)(migration|schema|prisma|\.sql$|model|entity|types?\.ts$|dto|serializer|form)")


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "HEAD"
    as_json = "--json" in sys.argv
    cfg = read_config(project / ".keel" / "config.yaml") if (project / ".keel" / "config.yaml").exists() else {}
    comp = cfg.get("compliance", {}) if isinstance(cfg.get("compliance"), dict) else {}
    extra_pii = [(p.strip(), "project pattern") for p in comp.get("pii_patterns", "").split("|") if p.strip()]

    excludes = [":(exclude).keel", ":(exclude)*.lock", ":(exclude)package-lock.json", ":(exclude)pnpm-lock.yaml", ":(exclude)yarn.lock"]
    diff = sh(["git", "diff", base, "--", ".", *excludes], project)
    untracked = sh(["git", "ls-files", "--others", "--exclude-standard"], project).split()
    for f in untracked:
        if f.startswith(".keel/") or f.endswith((".lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock")):
            continue
        try:
            body = (project / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        diff += f"\n+++ b/{f}\n" + "\n".join("+" + l for l in body.splitlines())

    findings = []
    # JSON manifests: compare dependency keys before and after instead of trusting line layout
    for manifest in ("package.json", "composer.json"):
        if (project / manifest).exists():
            try:
                after = json.loads((project / manifest).read_text(encoding="utf-8"))
                before_txt = sh(["git", "show", f"{base}:{manifest}"], project)
                before = json.loads(before_txt) if before_txt.strip() else {}
            except (ValueError, OSError):
                continue
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies", "require", "require-dev"):
                new = set((after.get(section) or {}).keys()) - set((before.get(section) or {}).keys())
                for dep in sorted(new):
                    findings.append({"klasse": "vorlage", "was": f"new dependency ({section})", "datei": manifest, "zeile": dep})
    current = ""
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            current = raw[6:] if raw.startswith("+++ b/") else raw[4:]
            continue
        if not raw.startswith("+") or raw.startswith("+++"):
            continue
        line = raw[1:]
        for pat, what in SECRETS:
            if re.search(pat, line):
                findings.append({"klasse": "block", "was": what, "datei": current, "zeile": line.strip()[:80]})
        name = Path(current).name
        if name in DEP_FILES and name not in ("package.json", "composer.json"):
            m = re.match(DEP_FILES[name], raw)
            if m and m.group(1) not in ("name", "version", "description", "main", "type", "private", "scripts", "test", "build", "typecheck", "lint"):
                findings.append({"klasse": "vorlage", "was": "new dependency", "datei": current, "zeile": m.group(1)})
        for pat, what in PII + extra_pii:
            if re.search(pat, line):
                schema = bool(SCHEMA_HINT.search(current))
                findings.append({"klasse": "pruefen", "was": f"personal data: {what}" + (" in schema or type" if schema else ""), "datei": current, "zeile": line.strip()[:80]})
                break
        for pat, what in EXTERNAL:
            m = re.search(pat, line)
            if m:
                findings.append({"klasse": "pruefen", "was": f"{what} to {m.group(m.lastindex)}", "datei": current, "zeile": line.strip()[:80]})
        for pat, what in LOGGING:
            if re.search(pat, line) and any(re.search(p, line) for p, _ in PII):
                findings.append({"klasse": "pruefen", "was": "personal data in a log statement", "datei": current, "zeile": line.strip()[:80]})

    order = {"block": 5, "vorlage": 4, "pruefen": 3}
    worst = max((order[f["klasse"]] for f in findings), default=0)
    result = {"ergebnis": {5: "block", 4: "vorlage", 3: "pruefen", 0: "frei"}[worst], "befunde": findings}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"compliance: {result['ergebnis']} ({len(findings)} Befunde)")
        for f in findings:
            print(f"  [{f['klasse']}] {f['was']}: {f['datei']}: {f['zeile']}")
    sys.exit(worst)


if __name__ == "__main__":
    main()
