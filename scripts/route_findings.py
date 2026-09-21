#!/usr/bin/env python3
"""Route the findings of an audit report: every finding line without an ID becomes a backlog item
(Herkunft: Audit) or a decision file, and the ID is written back into the report. Idempotent.

Usage: route_findings.py <project-dir> [<report.md>]     (default: newest report under .keel/work/audit/)
Prints one line per routed finding and a summary; exit 0.

Finding line format (from the Auditor): "- <Befund> – <Fundstelle> – wird Aufgabe | wird Vorlage"
After routing:                          "... – wird Aufgabe → BL-7"  /  "... – wird Vorlage → 2026-09-22-audit-1.md"
"""
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from frontmatter import parse as parse_fm  # noqa: E402

LINE = re.compile(r"^(- (?P<befund>.+?) – (?P<fundstelle>.+?) – wird (?P<ziel>Aufgabe|Vorlage))\s*$")


def newest_reports(project):
    out = []
    for d in ("audit", "architektur"):
        reports = sorted((project / ".keel" / "work" / d).glob("*.md"))
        if reports:
            out.append(reports[-1])
    return out


def propose_backlog(project, befund, fundstelle, report_name):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        titel = befund if len(befund) <= 80 else befund[:77].rstrip() + "…"
        f.write("---\n")
        f.write(f"titel: {json.dumps(titel, ensure_ascii=False)}\n")
        f.write(f"problem: {json.dumps(befund, ensure_ascii=False)}\n")
        f.write(f"warum: {json.dumps('Prüfbefund ' + report_name + ', Fundstelle: ' + fundstelle, ensure_ascii=False)}\n")
        f.write("herkunft: Audit\n---\n")
        path = f.name
    out = subprocess.run([sys.executable, str(Path(__file__).parent / "backlog.py"), "--project", str(project), "propose", path], capture_output=True, text=True)
    Path(path).unlink(missing_ok=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout)["id"]


def write_decision(project, befund, fundstelle, report_name, n):
    today = date.today().isoformat()
    pending = project / ".keel" / "decisions" / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    name = f"{today}-audit-{n}.md"
    while (pending / name).exists():
        n += 1
        name = f"{today}-audit-{n}.md"
    titel = befund if len(befund) <= 80 else befund[:77].rstrip() + "…"
    (pending / name).write_text(f"""---
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
""", encoding="utf-8")
    return name


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
    text = report.read_text(encoding="utf-8")
    data, _ = parse_fm(text)
    if not data or data.get("typ") not in ("pruefbericht", "architekturbericht"):
        print(f"{report.name}: kein Prüf- oder Architekturbericht (typ fehlt)")
        return
    if data.get("status") != "abweichungen":
        print(f"{report.name}: status passt, nichts zu routen")
        return
    lines = text.split("\n")
    routed, decisions = [], 0
    for i, line in enumerate(lines):
        m = LINE.match(line)
        if not m:
            continue
        befund, fundstelle, ziel = m.group("befund").strip(), m.group("fundstelle").strip(), m.group("ziel")
        if ziel == "Aufgabe":
            ref = propose_backlog(project, befund, fundstelle, report.name)
        else:
            decisions += 1
            ref = write_decision(project, befund, fundstelle, report.name, decisions)
        lines[i] = f"{m.group(1)} → {ref}"
        routed.append((ziel, ref, befund[:70]))
    if routed:
        report.write_text("\n".join(lines), encoding="utf-8")
    for ziel, ref, befund in routed:
        print(f"{ziel}: {ref}  {befund}")
    print(f"geroutet: {len(routed)} Befunde aus {report.name} ({sum(1 for z, _, _ in routed if z == 'Aufgabe')} Backlog, {sum(1 for z, _, _ in routed if z == 'Vorlage')} Vorlagen)")


if __name__ == "__main__":
    main()
