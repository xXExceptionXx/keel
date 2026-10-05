"""PreToolUse on Bash (observer that may allow): keel's own commands run without a permission prompt, so unattended
runs (claude -p, keel-run.sh) do not stop at the first script (System-ADR 0025).

Allowed is only a command whose every part is on a fixed list:
- keel's scripts and command line from this plugin's folder (also written as ${CLAUDE_PLUGIN_ROOT}),
- the project's test.command and test.acceptance, and the prefixes in freigaben.befehle (.keel/config.yaml),
- git with a fixed set of subcommands and no force; push not to main,
- cd into the project, date.
Command substitution, other variables, heredocs and redirections into files are never allowed. Anything else gets
no answer from this step and goes through Claude Code's permission flow as before. Deny and ask rules in the
settings still apply to an allowed call (Claude Code evaluates them regardless of the hook), and the guard runs
first: its refusal wins.

An allowed call outside a keel project (no .keel/config.yaml) does not exist: the step only answers there.
"""
import os
import shlex

from keel.services.hooks import legacy
from keel.services.hooks.base import Allow

VARIABLES = ("${CLAUDE_PLUGIN_ROOT}", "$CLAUDE_PLUGIN_ROOT", "${PWD}", "$PWD")
GIT_READ = {"status", "diff", "log", "show", "rev-parse", "rev-list", "ls-files", "ls-tree", "merge-base",
            "describe", "remote", "fetch", "config"}
GIT_WRITE = {"add", "commit", "switch", "merge", "mv", "tag", "pull", "push", "branch"}
REFUSED = {"push": {"--delete", "-d", "--mirror", "--all", "--tags", "--prune"},
           "commit": {"--amend", "--no-verify", "-n"},
           "merge": {"--abort", "-X", "--strategy-option"},
           "tag": {"-d", "--delete", "-f"},
           "mv": {"-f", "--force"}}


SEPARATORS = {"&&", "||", ";", "|", "\n"}
SAFE_REDIRECTS = (["2", ">&", "1"], ["2", ">", "/dev/null"], ["1", ">", "/dev/null"], [">", "/dev/null"])


def _parts(cmd):
    """The command as parts of tokens, split at && || ; | and newlines outside quotes; None when it uses anything
    not allowed: command substitution, other variables, heredocs, redirections other than to /dev/null or 2>&1,
    subshells, background jobs. Quoted text stays one token, so a commit message may contain < or ;."""
    if any(x in cmd for x in ("$(", "`", "<(", ">(", "<<")):
        return None
    rest = cmd
    for v in VARIABLES:
        rest = rest.replace(v, "")
    if "$" in rest:
        return None
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        return None
    parts, current = [], []
    for tok in tokens:
        if tok in SEPARATORS:
            if current:
                parts.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        parts.append(current)
    out = []
    for part in parts:
        for safe in SAFE_REDIRECTS:
            n = len(safe)
            while True:
                hit = next((i for i in range(len(part) - n + 1) if part[i:i + n] == safe), None)
                if hit is None:
                    break
                part = part[:hit] + part[hit + n:]
        if not part or any(set(t) <= set("();<>|&") for t in part):
            return None
        out.append(part)
    return out


def _expand(token, root, project):
    for v in ("${CLAUDE_PLUGIN_ROOT}", "$CLAUDE_PLUGIN_ROOT"):
        token = token.replace(v, root)
    for v in ("${PWD}", "$PWD"):
        token = token.replace(v, project)
    return token


def _inside(path, folder):
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def _keel_command(tokens, root):
    """python3 <root>/scripts/x.py ..., bash <root>/scripts/x.sh ..., <root>/bin/keel ..."""
    scripts = os.path.join(root, "scripts")
    if tokens[0] in ("python3", "bash") and len(tokens) > 1:
        target = tokens[1]
        return _inside(target, scripts) and os.path.isfile(target) and target.endswith((".py", ".sh"))
    return os.path.realpath(tokens[0]) == os.path.realpath(os.path.join(root, "bin", "keel"))


def _git(tokens, project):
    args = tokens[1:]
    if len(args) >= 2 and args[0] == "-C":
        if not _inside(args[1], project):
            return False
        args = args[2:]
    if not args:
        return False
    sub, flags = args[0], args[1:]
    if sub not in GIT_READ | GIT_WRITE:
        return False
    if any(f == "-f" or f.startswith("--force") or f in REFUSED.get(sub, ()) for f in flags):
        return False
    if sub == "push" and any(f.startswith("+") for f in flags):
        return False
    if sub == "config" and not any(f in ("--get", "--list", "-l") for f in flags):
        return False
    if sub == "remote" and flags and flags[0] not in ("-v", "get-url", "show"):
        return False
    if sub == "branch" and any(not f.startswith("--") and f not in ("-a", "-r", "-v", "-vv") for f in flags):
        return False  # listing only; creating and deleting branches goes through switch -c or the human
    if sub == "push" and ("main" in flags or any(":" in f for f in flags)):
        return False
    if sub == "pull" and "--ff-only" not in flags:
        return False
    return True


def _project_prefix(tokens, prefixes):
    for p in prefixes:
        try:
            want = shlex.split(p)
        except ValueError:
            continue
        if want and tokens[:len(want)] == want:
            return True
    return False


def run(hook):
    if hook.text("tool_name") != "Bash":
        return None
    project = str(hook.project)
    if not os.path.isfile(os.path.join(project, ".keel", "config.yaml")):
        return None
    cmd = hook.text("tool_input.command")
    parts = _parts(cmd) if cmd else None
    if not parts:
        return None
    root = str(legacy.PLUGIN_ROOT)
    prefixes = [hook.cfg("test.command", ""), hook.cfg("test.acceptance", "")]
    from keel.store import config
    extra = config.get(hook.config, "freigaben.befehle", [])
    prefixes += [str(x).strip() for x in (extra if isinstance(extra, list) else str(extra).split(","))]
    for part in parts:
        tokens = [_expand(t, root, project) for t in part]
        if _project_prefix(tokens, prefixes):
            continue
        if tokens[0] == "cd" and len(tokens) == 2 and _inside(tokens[1] if os.path.isabs(tokens[1])
                                                             else os.path.join(project, tokens[1]), project):
            continue
        if tokens[0] == "date" and all(t.startswith(("+", "-u")) for t in tokens[1:]):
            continue
        if tokens[0] == "git" and _git(tokens, project):
            continue
        if _keel_command(tokens, root):
            continue
        return None
    return Allow("keel: eigener Befehl, Testbefehl des Projekts oder sicheres git (System-ADR 0025)")
