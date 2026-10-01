#!/usr/bin/env python3
"""Review rounds with a threshold: snapshot per round, diffs for the Reviewer, mechanical verdict (System-ADR 0018).

Usage:
  review.py stand <project> <task-id>              snapshot the working tree (without .keel/) as a git tree,
                                                   stored as review_stand_r<runde> in the task; run by agent-gate
  review.py diff <project> <task-id> [--runde]     diff of the task: HEAD..snapshot of this round, including new files;
                                                   --runde: snapshot of the previous round..this round (the rework)
  review.py pruefen <project> <task-id>            validate the review file of the current round against its table
                                                   and the threshold, then write review_ergebnis and review_grund
                                                   into the task; run by agent-stop. Exit 1 with the reason if invalid.

Review file: frontmatter typ review, aufgabe, runde, status, blockierend, wichtig, anmerkung; one table row per finding:
  | Schweregrad | Herkunft | Fundstelle | Beschreibung |
Herkunft: neu (round 1), offen (from the previous round, not fixed), fix (new in the rework diff),
bestand (new in code the rework did not touch; only blockierend or anmerkung).

Verdict (review_ergebnis):
  bestanden   no severity above its threshold (review.schwelle_blockierend, review.schwelle_wichtig; default 0)
  nacharbeit  round 1, or (blockierend, wichtig) lexicographically lower than in the previous round
              while blockierend + wichtig does not rise
  vorlage     not lower than the previous round, or review.max_runden reached (plus review_zusatzrunden of the task)
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import ParseError, ReadError
from keel.store import config, frontmatter

SEVERITIES = ("blockierend", "wichtig", "anmerkung")
ORIGINS_FIRST = ("neu",)
ORIGINS_LATER = ("offen", "fix", "bestand")
EXCLUDE = ":(exclude).keel"


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def git(project, *args, env=None):
    out = subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, env=env)
    if out.returncode != 0:
        fail(f"git {' '.join(args)}: {out.stderr.strip()}", 2)
    return out.stdout


def task_path(project, task):
    return project / ".keel" / "work" / "tasks" / f"{task}.md"


def load(path):
    try:
        data, body = frontmatter.load(path)
    except (ReadError, ParseError) as exc:
        fail(str(exc), 2)
    if data is None:
        fail(f"{path}: no frontmatter found")
    return data, body


def update(path, **fields):
    """Write fields into the task, under a lock and atomically (N6)."""
    load(path)
    try:
        frontmatter.update(path, {k: str(v) for k, v in fields.items()})
    except (ReadError, ParseError) as exc:
        fail(str(exc), 2)


def cfg_int(project, key, default):
    try:
        tree = config.load(project)
    except (ReadError, ParseError) as exc:
        fail(f"review: {exc}", 2)
    return config.get_int(tree, f"review.{key}", default)


def snapshot(project):
    """Tree of the working tree including untracked files (respecting .gitignore); the real index stays untouched."""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(project, "read-tree", "HEAD", env=env)
        git(project, "add", "-A", "--", ".", EXCLUDE, env=env)
        return git(project, "write-tree", env=env).strip()


def cmd_stand(project, task):
    tp = task_path(project, task)
    data, _ = load(tp)
    runde = data.get("review_runde")
    if not runde or not str(runde).isdigit() or int(runde) < 1:
        fail(f"{tp}: review_runde fehlt oder ist kleiner 1")
    tree = snapshot(project)
    update(tp, review_ergebnis="", review_grund="", **{f"review_stand_r{runde}": tree})
    print(tree)


def cmd_diff(project, task, rework):
    data, _ = load(task_path(project, task))
    runde = int(data.get("review_runde") or 0)
    now = data.get(f"review_stand_r{runde}")
    if not now:
        fail(f"{task}: review_stand_r{runde} fehlt; der Stand wird beim Start des Reviewers festgehalten")
    if rework:
        before = data.get(f"review_stand_r{runde - 1}")
        if runde < 2 or not before:
            fail(f"{task}: kein Stand einer Vorrunde, Runde {runde}")
    else:
        before = git(project, "rev-parse", "HEAD^{tree}").strip()
    sys.stdout.write(git(project, "diff", before, now, "--", ".", EXCLUDE))


def findings(body):
    rows = []
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].lower() in SEVERITIES:
            rows.append({"schweregrad": cells[0].lower(), "herkunft": cells[1].lower(), "fundstelle": cells[2], "beschreibung": " | ".join(cells[3:])})
    return rows


def counts(data):
    try:
        return {s: int(data.get(s, "")) for s in SEVERITIES}
    except (ValueError, TypeError):
        return None


def sinking(before, now):
    """(blockierend, wichtig) is lexicographically lower and their sum does not rise: blocking findings weigh
    more, so (4, 0) to (0, 2) is progress, but trading one blocker for nine important findings, (1, 0) to
    (0, 9), is not."""
    return now < before and sum(now) <= sum(before)


def cmd_pruefen(project, task):
    tp = task_path(project, task)
    tdata, _ = load(tp)
    runde = int(tdata.get("review_runde") or 0)
    rev = project / ".keel" / "work" / "reviews" / f"{task}-r{runde}.md"
    data, body = load(rev)
    errors = []
    if data.get("typ") != "review":
        errors.append("typ muss review sein")
    if str(data.get("runde")) != str(runde):
        errors.append(f"runde ist '{data.get('runde')}', erwartet {runde}")
    declared = counts(data)
    if declared is None:
        errors.append("Frontmatter braucht blockierend, wichtig und anmerkung als Zahlen")
    rows = findings(body)
    actual = {s: sum(1 for r in rows if r["schweregrad"] == s) for s in SEVERITIES}
    if declared is not None and declared != actual:
        errors.append("Zahlen im Frontmatter passen nicht zur Tabelle: " + ", ".join(f"{s} {declared[s]} statt {actual[s]}" for s in SEVERITIES if declared[s] != actual[s]))
    allowed = ORIGINS_FIRST if runde == 1 else ORIGINS_LATER
    for r in rows:
        if r["herkunft"] not in allowed:
            errors.append(f"Herkunft '{r['herkunft']}' bei {r['fundstelle']} unzulässig in Runde {runde}, erlaubt: {', '.join(allowed)}")
        elif r["herkunft"] == "bestand" and r["schweregrad"] == "wichtig":
            errors.append(f"{r['fundstelle']}: neuer Befund in unverändertem Code ist blockierend oder Anmerkung, nicht wichtig")
    max_b = cfg_int(project, "schwelle_blockierend", 0)
    max_w = cfg_int(project, "schwelle_wichtig", 0)
    over = actual["blockierend"] > max_b or actual["wichtig"] > max_w
    expected = "befunde" if over else "bestanden"
    if data.get("status") != expected:
        errors.append(f"status ist '{data.get('status')}', nach Schwelle (blockierend ≤ {max_b}, wichtig ≤ {max_w}) muss er {expected} sein")
    if errors:
        fail(f"{rev.name}: " + "; ".join(errors))

    now = (actual["blockierend"], actual["wichtig"])
    fix = sum(1 for r in rows if r["herkunft"] == "fix" and r["schweregrad"] != "anmerkung")
    limit = cfg_int(project, "max_runden", 4) + int(tdata.get("review_zusatzrunden") or 0)
    if not over:
        result, reason = "bestanden", f"Runde {runde}: {now[0]} blockierend, {now[1]} wichtig, unter der Schwelle"
    elif runde == 1:
        result, reason = "nacharbeit", f"Runde 1: {now[0]} blockierend, {now[1]} wichtig"
    else:
        prev_path = rev.with_name(f"{task}-r{runde - 1}.md")
        prev = counts(load(prev_path)[0]) if prev_path.exists() else None
        before = (prev["blockierend"], prev["wichtig"]) if prev else None
        trend = f"Runde {runde - 1}: {before[0]}/{before[1]}, Runde {runde}: {now[0]}/{now[1]} (blockierend/wichtig), davon aus der Nacharbeit {fix}" if before else f"Runde {runde}: {now[0]}/{now[1]}, Vorrunde fehlt"
        if runde >= limit:
            result, reason = "vorlage", f"Höchstzahl von {limit} Runden erreicht; {trend}"
        elif before is None or not sinking(before, now):
            result, reason = "vorlage", f"Befunde sinken nicht; {trend}"
        else:
            result, reason = "nacharbeit", f"Befunde sinken; {trend}"
    update(tp, review_ergebnis=result, review_grund=reason, **{f"review_fix_r{runde}": fix})
    print(f"{result}: {reason}")


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ("stand", "diff", "pruefen"):
        fail(__doc__, 2)
    cmd, project, task = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3]
    if cmd == "stand":
        cmd_stand(project, task)
    elif cmd == "diff":
        cmd_diff(project, task, "--runde" in sys.argv[4:])
    else:
        cmd_pruefen(project, task)


if __name__ == "__main__":
    main()
