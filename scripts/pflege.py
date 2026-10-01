#!/usr/bin/env python3
"""Pflegeliste: Anmerkungen from passed reviews are kept instead of lost; the Architekt sorts them in the
weekly round (System-ADR 0018).

Usage:
  pflege.py sammeln <project> <review.md>      append the Anmerkungen of a passed review as open entries (idempotent);
                                               run by agent-stop after the Reviewer
  pflege.py offen <project>                    expire old open entries, then print the open ones (Markdown table)
  pflege.py setze <project> <status> <P-1,P-2,...> [<vermerk>]
                                               status: aufgabe | regel | verworfen | erledigt; vermerk e.g. the report

File: .keel/work/pflege.md, one table row per entry:
  | ID | Datum | Aufgabe | Fundstelle | Anmerkung | Status |
Open entries older than pflege.verfall_tage (default 42) become "verfallen".
Every change runs under a lock on the file and is written atomically, so parallel runs never hand out an ID twice.
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import ParseError, ReadError
from keel.store import config, frontmatter
from keel.store.io import atomic_write, file_lock

HEAD = """---
typ: pflegeliste
---

# Pflegeliste

Anmerkungen aus bestandenen Reviews. Der Architekt sichtet sie in der Wochenrunde: bündeln zu einer Pflegeaufgabe, als Prüfregel verankern oder verwerfen. Offene Einträge verfallen nach `pflege.verfall_tage`.

| ID | Datum | Aufgabe | Fundstelle | Anmerkung | Status |
| --- | --- | --- | --- | --- | --- |
"""
ROW = re.compile(r"^\| (P-\d+) \| (.*?) \| (.*?) \| (.*?) \| (.*) \| (.*?) \|\s*$")
TARGETS = ("aufgabe", "regel", "verworfen", "erledigt")


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def path_of(project):
    return project / ".keel" / "work" / "pflege.md"


def load(project):
    p = path_of(project)
    text = p.read_text(encoding="utf-8") if p.exists() else HEAD
    return text.rstrip("\n").split("\n")


def save(project, lines):
    atomic_write(path_of(project), "\n".join(lines) + "\n")


def rows(lines):
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if m:
            yield i, dict(zip(("id", "datum", "aufgabe", "fundstelle", "anmerkung", "status"), m.groups()))


def fmt(r):
    return f"| {r['id']} | {r['datum']} | {r['aufgabe']} | {r['fundstelle']} | {r['anmerkung']} | {r['status']} |"


def expire(project, lines):
    try:
        days = config.get_int(config.load(project), "pflege.verfall_tage", 42)
    except (ReadError, ParseError) as exc:
        fail(f"pflege: {exc}", 2)
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    changed = 0
    for i, r in list(rows(lines)):
        if r["status"] == "offen" and r["datum"] < cutoff:
            r["status"] = f"verfallen {date.today().isoformat()}"
            lines[i] = fmt(r)
            changed += 1
    return changed


def cmd_sammeln(project, review):
    try:
        data, body = frontmatter.load(review)
    except (ReadError, ParseError) as exc:
        fail(str(exc), 2)
    if not data or data.get("typ") != "review":
        fail(f"{review}: keine Review-Datei")
    if data.get("status") != "bestanden":
        print("pflege: Review nicht bestanden, nichts zu sammeln")
        return
    task = data.get("aufgabe", "?")
    lines = load(project)
    existing = {(r["aufgabe"], r["fundstelle"], r["anmerkung"]) for _, r in rows(lines)}
    n = max([int(r["id"][2:]) for _, r in rows(lines)] or [0])
    added = 0
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() != "anmerkung":
            continue
        fundstelle, text = cells[2], " / ".join(cells[3:]).replace("|", "/")
        if (task, fundstelle, text) in existing:
            continue
        n += 1
        lines.append(fmt({"id": f"P-{n}", "datum": date.today().isoformat(), "aufgabe": task, "fundstelle": fundstelle, "anmerkung": text, "status": "offen"}))
        existing.add((task, fundstelle, text))
        added += 1
    expired = expire(project, lines)
    if added or expired or not path_of(project).exists():
        save(project, lines)
    print(f"pflege: {added} Anmerkungen aus {review.name} gesammelt, {expired} verfallen")


def cmd_offen(project):
    lines = load(project)
    if expire(project, lines):
        save(project, lines)
    open_rows = [r for _, r in rows(lines) if r["status"] == "offen"]
    print("| ID | Datum | Aufgabe | Fundstelle | Anmerkung |\n| --- | --- | --- | --- | --- |")
    for r in open_rows:
        print(f"| {r['id']} | {r['datum']} | {r['aufgabe']} | {r['fundstelle']} | {r['anmerkung']} |")
    print(f"\noffen: {len(open_rows)}")


def cmd_setze(project, status, ids, note):
    if status not in TARGETS:
        fail(f"status muss einer von {', '.join(TARGETS)} sein")
    wanted = {i.strip() for i in ids.split(",") if i.strip()}
    lines = load(project)
    found = set()
    for i, r in list(rows(lines)):
        if r["id"] in wanted:
            r["status"] = f"{status} {note}".strip()
            lines[i] = fmt(r)
            found.add(r["id"])
    missing = wanted - found
    if missing:
        fail(f"unbekannte IDs: {', '.join(sorted(missing))}")
    save(project, lines)
    print(f"pflege: {len(found)} Einträge auf {status}")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("sammeln", "offen", "setze"):
        fail(__doc__, 2)
    cmd, project = sys.argv[1], Path(sys.argv[2]).resolve()
    if not ((cmd == "sammeln" and len(sys.argv) >= 4) or cmd == "offen" or (cmd == "setze" and len(sys.argv) >= 5)):
        fail(__doc__, 2)
    with file_lock(path_of(project)):
        if cmd == "sammeln":
            cmd_sammeln(project, Path(sys.argv[3]).resolve())
        elif cmd == "offen":
            cmd_offen(project)
        else:
            cmd_setze(project, sys.argv[3], sys.argv[4], " ".join(sys.argv[5:]))


if __name__ == "__main__":
    main()
