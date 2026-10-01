# Every Agent tool call the gate test sends: (subagent_type, prompt, run_in_background).
C = []
def add(t, p, bg=False): C.append((t, p, bg))
plans = ["p-entwurf", "p-entwurf-nobew", "p-problem", "p-atb", "p-nach", "p-geplant", "p-struktur", "p-abn", "p-abnrot-noacc", "p-integriert", "p-fehlt"]
tasks = ["T-geplant", "T-neu", "T-neu-noklar", "T-tb", "T-tb-empty", "T-nach", "T-review", "T-review-norunde", "T-rep", "T-rep-nach", "T-comp", "T-comp-noscan", "T-fertig", "T-fehlt"]
epics = ["e-skizze", "e-bewertet", "e-leit", "e-aktiv", "e-neu"]
for p in plans:
    add("keel:planer", f"Vorhaben: {p}")
    add("keel:tester", f"Vorhaben: {p}")
    for a in ["problemstellung", "abstimmung", "abnahme"]:
        add("keel:po", f"Anlass: {a}\nVorhaben: {p}\nBacklog: B1")
    add("keel:po", f"Anlass: problemstellung\nVorhaben: {p}")
    for a in ["bewertung", "strukturfrage"]:
        add("keel:architekt", f"Anlass: {a}\nVorhaben: {p}")
for t in tasks:
    for r in ["planer", "tester", "entwickler", "reviewer", "compliance"]:
        add(f"keel:{r}", f"Aufgabe: {t}\nVorhaben: p-geplant")
    add("keel:po", f"Anlass: klaerung\nVorhaben: p-geplant\nAufgabe: {t}")
    add("keel:po", f"Anlass: klaerung\nVorhaben: p-geplant")
for e in epics:
    for a in ["epic-skizze", "epic-abstimmung", "epic-abnahme"]:
        add("keel:po", f"Anlass: {a}\nEpic: {e}\nBacklog: B1")
    add("keel:po", f"Anlass: epic-skizze\nEpic: {e}")
    add("keel:architekt", f"Anlass: epic-bewertung\nEpic: {e}")
    for p in ["p-integriert", "p-geplant"]:
        add("keel:architekt", f"Anlass: epic-retrospektive\nEpic: {e}\nVorhaben: {p}")
    add("keel:architekt", f"Anlass: epic-retrospektive\nEpic: {e}")
for v in ["v-offen", "v-entschieden", "v-esk", "v-fehlt"]:
    add("keel:supervisor", f"Anlass: entscheiden\nVorlage: .keel/decisions/pending/{v}.md")
add("keel:supervisor", "Anlass: entscheiden")
add("keel:supervisor", "Anlass: kippen\nVorlage: .keel/decisions/pending/v-offen.md")
for r in ["auditor", "coach"]:
    add(f"keel:{r}", "Datum: 2026-09-26"); add(f"keel:{r}", "irgendwas")
for a in ["bestandsaufnahme", "wochenrunde"]:
    add("keel:architekt", f"Anlass: {a}\nDatum: 2026-09-26"); add("keel:architekt", f"Anlass: {a}")
for r in ["po", "architekt", "planer", "tester", "entwickler", "reviewer", "compliance"]:
    add(f"keel:{r}", "kein Feld")
add("keel:architekt", "Anlass: unsinn\nVorhaben: p-entwurf")
add("keel:unbekannt", "Aufgabe: T-tb")
add("keel:probe", "irgendwas")
add("general-purpose", "irgendwas")
add("keel:entwickler", "Aufgabe: T-tb", True)
