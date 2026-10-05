"""Bridge to the scripts under scripts/ that still hold their logic in main() (due.py, compliance_scan.py,
review.py, pflege.py, models.py, wiedervorlage.py). They run as a subprocess until M3/M4 move their logic into
the package. Exit codes keep their meaning; the caller decides what each one says."""
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[4]


def run(script, *args, merge=False, timeout=None):
    """(exit code, stdout, stderr) of scripts/<script>; with merge, stderr goes into stdout as with 2>&1."""
    path = PLUGIN_ROOT / "scripts" / script
    cmd = ["bash", str(path), *map(str, args)] if script.endswith(".sh") else [sys.executable, str(path), *map(str, args)]
    proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT if merge else subprocess.PIPE, timeout=timeout,
                          env=os.environ.copy())
    out = proc.stdout.decode("utf-8", "replace")
    err = "" if merge else proc.stderr.decode("utf-8", "replace")
    return proc.returncode, out, err


def strip(text):
    """Output as a shell $(...) gives it: trailing newlines removed."""
    return text.rstrip("\n")
