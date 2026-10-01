#!/usr/bin/env python3
"""The flow rules of keel in one place: when a role may start, and who acts next.

Usage: flow.py shell               shell assignments for hooks/agent-gate.sh
       flow.py bereit <project>    JSON: per role the objects it could start on now (for the monitor)

GATES lists, per role and occasion (Anlass), the object the role starts on and the status that object
must have. hooks/agent-gate.sh reads the status and nonempty lists from here and keeps its own checks
and messages; the monitor uses the same entries to show which roles are ready. The further conditions
(datei, abschnitt, feld) are checked in the gate's code and mirrored here for the monitor.
Entries marked nur_gate hold for the gate but are not shown as ready: the epic acceptance and retrospective
depend on the epic's progress, which the epic skill decides, not on a status alone.

PHASES, NEXT_PLAN and NEXT_TASK mirror skills/vorhaben/SKILL.md: who acts next for a plan or task status.
They describe the rule; the Lead still decides. Change them together with the skill.
"""
import json
import re
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.store.frontmatter import load_tolerant

# rolle.anlass -> object kind, required status, fields that must not be empty, further conditions
GATES = {
    "planer.planung": {"objekt": "plan", "status": ["abnahmetests-bereit", "nacharbeit"]},
    "planer.neuschnitt": {"objekt": "aufgabe", "status": ["neuschnitt"]},
    "po.problemstellung": {"objekt": "plan", "status": ["entwurf"], "oder_fehlt": True},
    "po.abstimmung": {"objekt": "plan", "status": ["entwurf"], "nonempty": ["bewertung"]},
    "po.klaerung": {"objekt": "aufgabe", "status": ["neuschnitt"], "abschnitt": "## Klärung"},
    "po.abnahme": {"objekt": "plan", "status": ["abnahme-bereit", "abnahme-rot"], "datei": "work/acceptance/{name}.md"},
    "po.epic-abstimmung": {"objekt": "epic", "status": ["bewertet", "leitentscheidungen-offen"]},
    "po.epic-abnahme": {"objekt": "epic", "status": ["aktiv"], "nur_gate": True},
    "architekt.bewertung": {"objekt": "plan", "status": ["entwurf"]},
    "architekt.strukturfrage": {"objekt": "plan", "status": ["strukturaenderung"]},
    "architekt.epic-bewertung": {"objekt": "epic", "status": ["skizze"]},
    "architekt.epic-retrospektive": {"objekt": "epic", "status": ["aktiv"], "nur_gate": True},
    "architekt.epic-retrospektive-vorhaben": {"objekt": "plan", "status": ["integriert"], "nur_gate": True},
    "tester.abnahmetests": {"objekt": "plan", "status": ["problemstellung"]},
    "tester.aufgabe": {"objekt": "aufgabe", "status": ["geplant", "neuschnitt"]},
    "entwickler.aufgabe": {"objekt": "aufgabe", "status": ["tests-bereit", "nacharbeit"], "nonempty": ["tests", "dateien"]},
    "entwickler.reparatur": {"objekt": "aufgabe", "status": ["reparatur", "nacharbeit"]},
    "reviewer.aufgabe": {"objekt": "aufgabe", "status": ["review"], "nonempty": ["review_runde"]},
    "compliance.aufgabe": {"objekt": "aufgabe", "feld": {"compliance": "pruefen"}, "datei": "work/compliance/{name}.scan.md"},
    "supervisor.entscheiden": {"objekt": "vorlage", "status": ["offen"], "nicht": ["eskaliert"]},
}

# A hard due item (due.py) blocks every role except the ones that satisfy it.
DUE_ROLES = {
    "briefing": ["supervisor"],
    "audit": ["auditor"],
    "coach": ["coach"],
    "architektur": ["architekt"],
    "tagesabschluss": ["entwickler", "reviewer"],
}

# Roles that start by date or due item rather than by an object's status.
BY_DUE = {"auditor": "audit", "coach": "coach"}

PHASES = [
    ("Problemstellung", ["entwurf"], "PO und Architekt"),
    ("Abnahmetests", ["problemstellung"], "Tester"),
    ("Planung", ["abnahmetests-bereit", "strukturaenderung"], "Planer"),
    ("Umsetzung", ["geplant", "in-arbeit", "nacharbeit"], "Tester, Entwickler, Compliance, Reviewer"),
    ("Abnahme", ["abnahme-bereit", "abnahme-rot"], "PO"),
    ("Integration", ["abgenommen"], "Lead"),
    ("Integriert", ["integriert", "abgeschlossen"], ""),
]
NEXT_PLAN = {
    "entwurf": "Architekt bewertet, PO stimmt ab (höchstens zwei Runden)",
    "problemstellung": "Tester schreibt die Abnahmetests",
    "abnahmetests-bereit": "Planer schneidet die Aufgaben",
    "strukturaenderung": "Lead schreibt eine Vorlage zur Strukturfrage",
    "geplant": "Aufgabenzyklus: erste offene Aufgabe",
    "in-arbeit": "Aufgabenzyklus: erste offene Aufgabe",
    "nacharbeit": "Planer schneidet Aufgaben aus der Nacharbeit des PO",
    "abnahme-bereit": "PO nimmt ab",
    "abnahme-rot": "PO schreibt Nacharbeit aus den roten Abnahmetests",
    "abgenommen": "Lead integriert in die Basis beim nächsten Aufruf",
    "blockiert": "wartet auf eine Entscheidung (Supervisor oder Briefing)",
}
NEXT_TASK = {
    "geplant": "Tester",
    "tests-bereit": "Entwickler",
    "in-arbeit": "Entwickler",
    "nacharbeit": "Entwickler",
    "fertig-gemeldet": "Compliance-Scan, dann Reviewer",
    "review": "Reviewer",
    "testeinspruch": "Planer (Neuschnitt)",
    "budget-erschoepft": "Planer (Neuschnitt)",
    "neuschnitt": "Planer (Neuschnitt) oder PO (Klärung)",
}

# After the Reviewer the task stays in "review"; the hook's verdict says what comes next (System-ADR 0018).
NEXT_AFTER_REVIEW = {
    "bestanden": "Lead committet",
    "nacharbeit": "Entwickler (Nacharbeit, danach erneut Review)",
    "vorlage": "Lead schreibt Review-Vorlage an den Supervisor",
}


def next_task(task):
    """Next step for a task from its frontmatter."""
    if task.get("status") == "review" and task.get("review_ergebnis") in NEXT_AFTER_REVIEW:
        return NEXT_AFTER_REVIEW[task["review_ergebnis"]]
    return NEXT_TASK.get(task.get("status"))


ROLES = ["supervisor", "po", "architekt", "planer", "tester", "entwickler", "compliance", "reviewer", "auditor", "coach"]


def shell_name(key):
    return re.sub(r"[^A-Za-z0-9]", "_", key)


def shell():
    """KEEL_S_<rolle_anlass>=<status,...> and KEEL_N_<rolle_anlass>=<fields,...>, KEEL_DUE_<art>=<roles>."""
    out = []
    for key, g in GATES.items():
        if g.get("status"):
            out.append(f"KEEL_S_{shell_name(key)}='{','.join(g['status'])}'")
        if g.get("nonempty"):
            out.append(f"KEEL_N_{shell_name(key)}='{','.join(g['nonempty'])}'")
    for art, roles in DUE_ROLES.items():
        out.append(f"KEEL_DUE_{shell_name(art)}='{' '.join(roles)}'")
    return "\n".join(out)


def _objects(keel, kind):
    folder = {"plan": "work/plans", "aufgabe": "work/tasks", "epic": "work/epics", "vorlage": "decisions/pending"}[kind]
    d = keel / folder
    for p in sorted(d.glob("*.md")) if d.exists() else []:
        if p.name.endswith(".bewertung.md"):
            continue
        loaded = load_tolerant(p)
        if loaded is None:
            continue
        data, body = loaded
        typ = {"aufgabe": "aufgabe", "plan": "plan", "epic": "epic", "vorlage": "vorlage"}[kind]
        if data.get("typ") != typ:
            continue
        name = data.get("id") if kind == "aufgabe" and data.get("id") else p.stem
        yield name, p, data, body


def _empty(v):
    return v is None or v == "" or v == []


def satisfied(keel, g, name, path, data, body):
    """Whether an existing object meets the entry condition of a gate entry."""
    if g.get("status") and data.get("status") not in g["status"]:
        return False
    if any(_empty(data.get(k)) for k in g.get("nonempty", [])):
        return False
    if any(str(data.get(k, "")) != v for k, v in g.get("feld", {}).items()):
        return False
    if any(not _empty(data.get(k)) for k in g.get("nicht", [])):
        return False
    if g.get("abschnitt") and not re.search(rf"^{re.escape(g['abschnitt'])}", body, re.M):
        return False
    if g.get("datei") and not (keel / g["datei"].format(name=name)).is_file():
        return False
    return True


def bereit(project):
    """Per role: the objects it could start on now, by the gate's entry conditions. Roles that start by
    due item (auditor, coach) or by date (architect rounds) are left to the due list."""
    keel = Path(project) / ".keel"
    out = {r: [] for r in ROLES}
    for key, g in GATES.items():
        if g.get("nur_gate") or g.get("oder_fehlt"):
            continue
        role, anlass = key.split(".", 1)
        for name, path, data, body in _objects(keel, g["objekt"]):
            if satisfied(keel, g, name, path, data, body):
                out[role].append({"anlass": anlass, "ref": name, "pfad": str(path.relative_to(project))})
    return out


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "shell":
        print(shell())
    elif len(sys.argv) >= 3 and sys.argv[1] == "bereit":
        print(json.dumps(bereit(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
