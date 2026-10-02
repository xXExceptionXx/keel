"""git for the core: branch, base, objects of other branches. Every failure is a ToolError (exit 2)."""
import subprocess

from keel.domain.errors import ToolError
from keel.store import config


def run(project, *args, check=True):
    """stdout of `git -C project args`; a ToolError when git is missing or fails (with check)."""
    try:
        r = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True)
    except OSError as exc:
        raise ToolError(f"git nicht ausführbar: {exc}") from exc
    if check and r.returncode != 0:
        raise ToolError(f"git {' '.join(args)}: {r.stderr.strip() or r.returncode}")
    return r.stdout if check else r


def current_branch(project):
    """Name of the checked-out branch; empty on a detached HEAD."""
    return run(project, "branch", "--show-current").strip()


def ref_exists(project, ref):
    return run(project, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}", check=False).returncode == 0


def base(project):
    """The configured base branch (git.base_branch). Without that ref, a fresh repository or a test fixture,
    the current branch counts as base."""
    name = config.get(config.load(project), "git.base_branch") or "main"
    return name if ref_exists(project, name) else (current_branch(project) or name)


def on_base(project):
    return current_branch(project) == base(project)


def merge_base(project, a, b):
    return run(project, "merge-base", a, b).strip()


def diff_names(project, a, b, path, diff_filter="AM"):
    """Files below path that differ between a and b, limited to the filter (A added, M modified, D deleted)."""
    out = run(project, "diff", "--name-only", f"--diff-filter={diff_filter}", a, b, "--", path)
    return [line for line in out.splitlines() if line.strip()]


def ls_tree(project, ref, path):
    """Names of the files directly below path in ref; empty when path does not exist there."""
    out = run(project, "ls-tree", "--name-only", f"{ref}:{path}", check=False)
    return [] if out.returncode != 0 else [line for line in out.stdout.splitlines() if line.strip()]


def show(project, ref, path):
    """Text of path in ref, or None when it does not exist there."""
    r = run(project, "show", f"{ref}:{path}", check=False)
    return r.stdout if r.returncode == 0 else None


def is_tracked(project, path):
    return run(project, "ls-files", "--error-unmatch", "--", str(path), check=False).returncode == 0


def mv(project, src, dst):
    run(project, "mv", "--", str(src), str(dst))


def dirty(project, path):
    """Uncommitted changes below path, as porcelain lines."""
    return [line for line in run(project, "status", "--porcelain", "--", path).splitlines() if line.strip()]
