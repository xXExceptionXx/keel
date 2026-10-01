#!/usr/bin/env python3
"""Run a command with a time limit; macOS ships no timeout(1).

Usage: timeout.py <seconds> -- <command> [args...]
The command runs in its own process group. When the limit is hit, the group gets SIGTERM, after 5 seconds
SIGKILL. Exit code: the command's, 124 when the limit was hit, 2 on usage errors.
"""
import os
import signal
import subprocess
import sys


def main():
    try:
        sep = sys.argv.index("--")
        seconds = float(sys.argv[1])
        cmd = sys.argv[sep + 1:]
    except (ValueError, IndexError):
        cmd = None
    if not cmd or seconds <= 0:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    proc = subprocess.Popen(cmd, start_new_session=True)
    try:
        rc = proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        for sig, grace in ((signal.SIGTERM, 5), (signal.SIGKILL, None)):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                proc.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        print(f"timeout: abgebrochen nach {seconds:g} s", file=sys.stderr)
        sys.exit(124)
    sys.exit(128 - rc if rc < 0 else rc)


if __name__ == "__main__":
    main()
