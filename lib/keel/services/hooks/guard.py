"""PreToolUse on Bash (gate): the second safety net behind the deny rules in .claude/settings.json.

Deny rules match command prefixes; this step matches patterns anywhere in the command. A pattern list stays a
guard rail with gaps, never a boundary: the deny rules and the roles' instructions are the first net. Every
pattern is tried on each line of the command on its own, as grep did in the Bash version.

U4 (kern-befunde.md): force push by refspec (+main), rm with long options or a quoted $HOME, find -delete outside
the working directory, cd to / or home followed by a recursive rm, and deleting a remote branch that is not merged.
"""
import re

S = r"[ \t\r\f\v]"  # [[:space:]] inside one line
DANGER = r"""["']?(/|~|\$\{?HOME\}?|\.\.)"""
RM_OPT = r"(-[a-zA-Z]*[rRf][a-zA-Z]*|--recursive|--force|--no-preserve-root)"


def _any(pattern, cmd, flags=0):
    rx = re.compile(pattern, flags)
    return any(rx.search(line) for line in cmd.split("\n"))


def segments(cmd):
    """Command segments split at && || ; | and newlines, without redirections, stripped."""
    out = []
    for seg in re.split(r"&&|\|\||;|\||\n", cmd):
        seg = re.sub(rf"{S}+[0-9]*>&?[0-9]*{S}*[^ \t\r\f\v]*", "", seg).strip()
        if seg:
            out.append(seg)
    return out


def _merged(hook, remote, branch, base):
    """Whether remote/branch is contained in the base branch (remote/base, else the local base)."""
    import subprocess

    proj = str(hook.project)

    def git(*args):
        return subprocess.run(["git", "-C", proj, *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    tip = git("rev-parse", "-q", "--verify", f"refs/remotes/{remote}/{branch}^{{commit}}")
    if tip.returncode != 0:
        return False
    for b in (f"refs/remotes/{remote}/{base}", f"refs/heads/{base}"):
        if git("rev-parse", "-q", "--verify", f"{b}^{{commit}}").returncode == 0:
            return git("merge-base", "--is-ancestor", tip.stdout.decode().strip(), b).returncode == 0
    return False


def _deny(hook, reason):
    hook.try_record("denied", {"hook": "guard", "role": "", "reason": reason})
    from keel.services.hooks.base import Refuse
    return Refuse(f"keel guard: {reason}")


def run(hook):
    cmd = hook.text("tool_input.command")
    if not cmd:
        return None

    # Git history and remote rewrites
    if _any(rf"git{S}+push\b.*({S}-f\b|--force|{S}\+[^ \t\r\f\v])", cmd):
        return _deny(hook, "force push is not allowed")
    if _any(rf"git{S}+push\b.*({S}:[^ \t\r\f\v]|--delete)", cmd):
        fp = hook.cfg("git.feature_prefix", "feature/")
        xp = hook.cfg("git.fix_prefix", "fix/")
        base = hook.cfg("git.base_branch", "main")
        allowed = rf"^git{S}+push{S}+([^ \t\r\f\v]+){S}+(--delete{S}+|:)(({re.escape(fp)}|{re.escape(xp)})[A-Za-z0-9._/-]+)$"
        for seg in segments(cmd):
            if not re.search(rf"git{S}+push\b.*({S}:[^ \t\r\f\v]|--delete)", seg):
                continue
            m = re.search(allowed, seg)
            if not m:
                return _deny(hook, f"deleting remote branches is only allowed for merged {fp}* and {xp}* branches")
            if not _merged(hook, m.group(1), m.group(3), base):
                return _deny(hook, f"deleting remote branches is only allowed for merged {fp}* and {xp}* branches; "
                                   f"{m.group(1)}/{m.group(3)} is not merged into {base} (git fetch first?)")

    # File deletion outside the working directory
    if _any(rf"""(^|[ \t\r\f\v;&|"'(])rm{S}+({RM_OPT}{S}+)+([^ \t\r\f\v]*{S}+)*{DANGER}""", cmd):
        return _deny(hook, "recursive delete on an absolute path, home or parent directory is not allowed")
    segs = segments(cmd)
    for i, seg in enumerate(segs):
        if re.match(rf"cd({S}+{DANGER}[^ \t\r\f\v]*)?$", seg) and \
                any(re.search(rf"(^|{S})rm{S}+({RM_OPT}{S}+)+", later + " ") for later in segs[i + 1:]):
            return _deny(hook, "recursive delete after changing to an absolute path, home or parent directory "
                               "is not allowed")
    if _any(rf"(^|[ \t\r\f\v;&|])find{S}+{DANGER}.*{S}(-delete\b|-exec{S}+rm\b)", cmd):
        return _deny(hook, "find with -delete or -exec rm on an absolute path, home or parent directory is not allowed")

    # Databases and infrastructure
    if _any(rf"\b(drop{S}+(database|table|schema)|truncate{S}+table)\b", cmd, re.I):
        return _deny(hook, "dropping or truncating database objects is not allowed")
    if _any(rf"docker{S}+(system|volume|container|image){S}+prune|mkfs\.|dd{S}+if=|:\(\){S}*\{{", cmd):
        return _deny(hook, "destructive system command is not allowed")

    # Reading credentials: roles never need the values, scripts take them from the environment themselves
    if _any(rf"(^|[ \t\r\f\v;&|])(env|printenv|export -p|set)({S}*$|{S}*\|)|gh{S}+auth{S}+token|"
            r"\$\{?[A-Z_]*(TOKEN|SECRET|KEY|PASSWORD)[A-Z_]*\}?|"
            r"(cat|less|head|tail|grep)[^|]*(\.env\b|\.netrc|id_rsa|credentials\.json|\.claude\.json)", cmd):
        return _deny(hook, "reading credentials or the environment is not allowed; scripts read what they need themselves")

    # Remote code execution
    if _any(rf"(curl|wget)[^|]*\|{S}*(sudo{S}+)?(ba|z)?sh\b", cmd):
        return _deny(hook, "piping downloaded content into a shell is not allowed")
    return None
