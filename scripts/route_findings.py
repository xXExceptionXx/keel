#!/usr/bin/env python3
"""Route the findings of an audit report: every finding line without an ID becomes a backlog item
(Herkunft: Audit, or Pflege for "wird Pflege") or a decision file, and the ID is written back into the report. Idempotent:
the report is written back atomically after every routed finding (F6), so an abort leaves nothing to route twice.

Usage: route_findings.py <project-dir> [<report.md>]     (default: newest report under .keel/work/audit/)
Prints one line per routed finding and a summary; exit 0.

Finding line format (from the Auditor): "- <Befund> – <Fundstelle> – wird Aufgabe | wird Vorlage | wird Pflege"
After routing:                          "... – wird Aufgabe → BL-7"  /  "... – wird Vorlage → 2026-09-22-audit-1.md"
"""
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import _keel  # noqa: F401
from keel.store.frontmatter import parse as parse_fm
from keel.store.io import atomic_write, create_exclusive, file_lock

LINE = re.compile(r"^(- (?P<befund>.+?) – (?P<fundstelle>.+?) – wird (?P<ziel>Aufgabe|Vorlage|Pflege))\s*$")


def newest_reports(project):
    out = []
    for d in ("audit", "architektur"):
        reports = sorted((project / ".keel" / "work" / d).glob("*.md"))
        if reports:
            out.append(reports[-1])
    return out


def propose_backlog(project, befund, fundstelle, report_name, herkunft="Audit"):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        titel = befund if len(befund) <= 80 else befund[:77].rstrip() + "…"
        f.write("---\n")
        f.write(f"titel: {json.dumps(titel, ensure_ascii=False)}\n")
        f.write(f"problem: {json.dumps(befund, ensure_ascii=False)}\n")
        f.write(f"warum: {json.dumps('Prüfbefund ' + report_name + ', Fundstelle: ' + fundstelle, ensure_ascii=False)}\n")
        f.write(f"herkunft: {herkunft}\n---\n")
        path = f.name
    out = subprocess.run([sys.executable, str(Path(__file__).parent / "backlog.py"), "--project", str(project), "propose", path], capture_output=True, text=True)
    Path(path).unlink(missing_ok=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout)["id"]


def write_decision(project, befund, fundstelle, report_name, n):
    today = date.today().isoformat()
    pending = project / ".keel" / "decisions" / "pending"
    titel = befund if len(befund) <= 80 else befund[:77].rstrip() + "…"
    text = f"""---
typ: vorlage
titel: {json.dumps(titel, ensure_ascii=False)}
von: Auditor
datum: {today}
status: offen
entscheidung:
entschieden:
quelle: {report_name}
---

# Vorlage: {titel}

**Problem:** {befund} Fundstelle: {fundstelle}.

**Optionen:**
1. Beheben: als Backlog-Element aufnehmen und einplanen – Folgen: Aufwand jetzt, Befund erledigt.
2. Maßstab anpassen: Zielbild, Qualitätsmerkmale, Befugnisse oder Architektur so ändern, dass der Zustand erlaubt ist – Folgen: Regel wird ergänzt, kein Einzelfall mehr.
3. Zurückstellen mit Begründung – Folgen: Befund bleibt dokumentiert offen, der Auditor führt ihn nicht erneut auf.

**Empfehlung:** vom Auditor als Vorlage eingestuft, weil er außerhalb der Befugnisse des PO liegt; die Abwägung ist deine.

**Warum ich nicht selbst entscheide:** Vermerk des Auditors „wird Vorlage“ (außerhalb der Befugnisse des PO).
"""
    while not create_exclusive(pending / f"{today}-audit-{n}.md", text):
        n += 1
    return f"{today}-audit-{n}.md"


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    reports = [Path(sys.argv[2]).resolve()] if len(sys.argv) > 2 else newest_reports(project)
    if not reports:
        print("kein Prüfbericht vorhanden")
        return
    for report in reports:
        route(project, report)


def route(project, report):
    with file_lock(report):
        _route(project, report)


def _route(project, report):
    text = report.read_text(encoding="utf-8")
    data, _ = parse_fm(text, source=str(report))
    if not data or data.get("typ") not in ("pruefbericht", "architekturbericht"):
        print(f"{report.name}: kein Prüf- oder Architekturbericht (typ fehlt)")
        return
    if data.get("status") != "abweichungen" and not any(LINE.match(l) for l in text.split("\n")):
        print(f"{report.name}: status passt, nichts zu routen")
        return
    lines = text.split("\n")
    routed, decisions = [], 0
    for i, line in enumerate(lines):
        m = LINE.match(line)
        if not m:
            continue
        befund, fundstelle, ziel = m.group("befund").strip(), m.group("fundstelle").strip(), m.group("ziel")
        if ziel in ("Aufgabe", "Pflege"):
            ref = propose_backlog(project, befund, fundstelle, report.name, "Pflege" if ziel == "Pflege" else "Audit")
        else:
            decisions += 1
            ref = write_decision(project, befund, fundstelle, report.name, decisions)
        lines[i] = f"{m.group(1)} → {ref}"
        atomic_write(report, "\n".join(lines))
        routed.append((ziel, ref, befund[:70]))
    for ziel, ref, befund in routed:
        print(f"{ziel}: {ref}  {befund}")
    print(f"geroutet: {len(routed)} Befunde aus {report.name} ({sum(1 for z, _, _ in routed if z != 'Vorlage')} Backlog, {sum(1 for z, _, _ in routed if z == 'Vorlage')} Vorlagen)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # what was routed is already written back; a rerun continues there
        print(f"route_findings: abgebrochen: {exc!r}", file=sys.stderr)
        sys.exit(2)
