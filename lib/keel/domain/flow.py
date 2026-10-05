"""The flow rules of keel as data: when a role may start, which roles a due item lets through, who acts next.

GATES lists, per role and occasion (Anlass), the object the role starts on and the status that object
must have. The agent gate (keel.services.hooks.agent_gate) takes the status and nonempty lists from here and
keeps its own checks and messages; the monitor uses the same entries to show which roles are ready. The further
conditions (datei, abschnitt, feld) are checked in the gate's code and mirrored here for the monitor.
Entries marked nur_gate hold for the gate but are not shown as ready: the epic acceptance and retrospective
depend on the epic's progress, which the epic skill decides, not on a status alone.

PHASES, NEXT_PLAN and NEXT_TASK mirror skills/vorhaben/SKILL.md: who acts next for a plan or task status.
They describe the rule; the Lead still decides. Change them together with the skill.
"""

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
    ("Integriert", ["integriert", "abgeschlossen", "verworfen"], ""),
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




def status(key):
    """Allowed status list of a gate entry, e.g. status("tester.aufgabe")."""
    return list(GATES[key].get("status", []))


def nonempty(key):
    """Fields of a gate entry that must not be empty."""
    return list(GATES[key].get("nonempty", []))
