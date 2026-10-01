#!/usr/bin/env python3
"""keel metrics: derive the learning-loop numbers from artifacts and raw hook data.

Usage: metrics.py <project-dir> [--since YYYY-MM-DD] [--json]

Sources: events of the runtime folder (keel path events: role starts/stops, blocked stops, budgets),
subagent transcripts (tokens), git log (task diffs), .keel/work (tasks, reviews, audits),
.keel/decisions and .keel/adr. Corridors come from .keel/config.yaml under `korridore`.
A second table splits run outcomes by the model that ran them (System-ADR 0015), for the Coach after a model switch.
Working roles never call this; it is for the human and the Coach.
Unreadable files and values that are not numbers or dates are skipped, never a crash (F8).
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import KeelError
from keel.store import config, events
from keel.store.frontmatter import fields_tolerant as fields
from keel.store.paths import Paths
from models import runs as model_runs, switches as model_switches  # noqa: E402
from review import findings as review_findings  # noqa: E402


def as_int(value, default=0):
    """A whole number from a frontmatter value; default for anything else (`runde: zwei`)."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_date(value):
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


def text_of(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def in_corridor(value, corridor):
    if value is None or not corridor:
        return None
    m = re.match(r"^\s*([\d.]+)\s*-\s*([\d.]+)\s*$", str(corridor))
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    return lo <= float(value) <= hi


def token_usage(transcript):
    """Sum output tokens and take the largest context seen in a subagent transcript."""
    out, ctx = 0, 0
    try:
        for line in Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or rec.get("type") != "assistant":
                continue
            u = (rec.get("message") or {}).get("usage") or {}
            out += u.get("output_tokens", 0)
            ctx = max(ctx, u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0))
    except OSError:
        pass
    return out, ctx


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    paths = Paths(project)
    since = None
    if "--since" in sys.argv:
        i = sys.argv.index("--since") + 1
        text = sys.argv[i] if i < len(sys.argv) else ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            # a calendar day starts at local midnight, as in due.py; a time without zone counts as UTC
            since = datetime.combine(date.fromisoformat(text), datetime.min.time()).astimezone()
        else:
            since = events.parse_ts(text)
        if since is None:
            print("metrics: --since braucht ein Datum oder einen Zeitpunkt (ISO 8601)", file=sys.stderr)
            sys.exit(2)
    as_json = "--json" in sys.argv
    try:
        corridors = config.section(config.load_file(paths.config), "korridore")
    except KeelError as exc:
        print(f"metrics: nicht prüfbar: {exc}", file=sys.stderr)
        sys.exit(2)

    # ---- events
    read = events.read(paths.events, since=since)
    evs = read.events
    stops = [e for e in evs if e.get("event") == "agent_stop"]
    blocked = [e for e in evs if e.get("event") == "stop_blocked"]
    budget = [e for e in evs if e.get("event") == "budget_exhausted"]
    context_alarms = [e for e in evs if e.get("event") == "context_alarm"]

    # ---- tokens per task from subagent transcripts
    tokens_by_ref = defaultdict(int)
    for e in stops:
        if isinstance(e.get("transcript"), str):
            out, _ = token_usage(e["transcript"])
            tokens_by_ref[e.get("ref") or "?"] += out
    task_refs = [r for r in tokens_by_ref if re.match(r"^[A-Z]+\d*-T\d+$", r)]
    tokens_per_task = round(sum(tokens_by_ref[r] for r in task_refs) / len(task_refs) / 1000, 1) if task_refs else None

    # ---- tasks and reviews
    tasks_dir = project / ".keel" / "work" / "tasks"
    tasks = {p.stem: fields(p) for p in tasks_dir.glob("*.md")} if tasks_dir.exists() else {}  # no date: all
    neuschnitt = [t for t in tasks.values() if as_int(t.get("neuschnitt_runden")) > 0]
    reviews_dir = project / ".keel" / "work" / "reviews"
    reviews = [fields(p) for p in reviews_dir.glob("*.md")] if reviews_dir.exists() else []
    rounds = defaultdict(int)
    for r in reviews:
        rounds[r.get("aufgabe")] = max(rounds[r.get("aufgabe")], as_int(r.get("runde")))
    review_rounds = round(sum(rounds.values()) / len(rounds), 2) if rounds else None
    befunde = [r for r in reviews if r.get("status") == "befunde"]
    # rework rounds whose rework introduced findings above Anmerkung (System-ADR 0018)
    rework = []
    for p in (reviews_dir.glob("*.md") if reviews_dir.exists() else []):
        text = text_of(p)
        if as_int(fields(p).get("runde")) >= 2:
            rework.append(any(r["herkunft"] == "fix" and r["schweregrad"] != "anmerkung" for r in review_findings(text)))
    fix_prozent = round(100 * sum(rework) / len(rework)) if rework else None
    pflege_file = project / ".keel" / "work" / "pflege.md"
    pflege_status = re.findall(r"^\| P-\d+ \|.*\| (\S+)[^|]*\|\s*$", text_of(pflege_file), flags=re.M)
    pflege_closed = [st for st in pflege_status if st != "offen"]
    pflege_verfallen = round(100 * pflege_closed.count("verfallen") / len(pflege_closed)) if pflege_closed else None

    # ---- diff lines per task from git
    diff_lines = []
    try:
        log = subprocess.run(["git", "log", "--all", "--format=%H%x09%s", "--grep=Keel-Task:"], cwd=project, capture_output=True, text=True).stdout
        for line in log.splitlines():
            sha, subject = line.split("\t", 1)
            if not re.match(r"^[A-Z]+\d*-T\d+:", subject):
                continue
            ns = subprocess.run(["git", "show", "--numstat", "--format=", sha, "--", ".", ":(exclude).keel"], cwd=project, capture_output=True, text=True).stdout
            total = sum(int(a) + int(b) for a, b, _ in (l.split("\t") for l in ns.splitlines() if l.strip()) if a.isdigit() and b.isdigit())
            diff_lines.append(total)
    except (OSError, ValueError):
        pass
    diff_avg = round(sum(diff_lines) / len(diff_lines)) if diff_lines else None

    # ---- decisions
    dec = project / ".keel" / "decisions"
    pending = list((dec / "pending").glob("*.md")) if (dec / "pending").exists() else []
    done_dec = [fields(p) for p in (dec / "done").glob("*.md")] if (dec / "done").exists() else []
    all_dec = [fields(p) for p in pending] + done_dec
    weeks = 1.0
    dates = sorted(d for d in (as_date(x.get("datum")) for x in all_dec) if d)
    if len(dates) >= 2:
        weeks = max(1.0, (dates[-1] - dates[0]).days / 7)
    human_dec = [d for d in all_dec if d.get("eskaliert") == "Supervisor" or d.get("von") == "Coach" or d.get("entscheider") == "Mensch" or (not d.get("entscheider") and not d.get("eskaliert") and d.get("status") == "entschieden")]
    vorlagen_pro_woche = round(len(human_dec) / weeks, 1)
    durations = []
    for d in done_dec:
        start, end = as_date(d.get("datum")), as_date(d.get("entschieden"))
        if start and end:
            durations.append((end - start).days)
    entscheidungsdauer = round(sum(durations) / len(durations), 1) if durations else None

    # ---- ADRs
    adr_dir = project / ".keel" / "adr"
    adrs = [fields(p) for p in adr_dir.glob("[0-9]*.md") if p.stem != "0000-vorlage"] if adr_dir.exists() else []
    delegated = [a for a in adrs if "delegiert" in str(a.get("status", "")) or (a.get("entscheider") == "PO")]
    kippt = [a for a in delegated if str(a.get("status", "")).startswith(("Rejected", "Superseded"))]
    gekippt_prozent = round(100 * len(kippt) / len(delegated)) if delegated else None

    # ---- supervisor
    sup = [a for a in adrs if a.get("entscheider") == "Supervisor"]
    sup_kippt = [a for a in sup if str(a.get("status", "")).startswith(("Rejected", "Superseded"))]
    sup_gekippt_prozent = round(100 * len(sup_kippt) / len(sup)) if sup else None
    eskaliert = [d for d in all_dec if d.get("eskaliert") == "Supervisor"]
    sup_entschieden = [d for d in all_dec if d.get("entscheider") == "Supervisor"]
    eskalationsquote = round(100 * len(eskaliert) / (len(eskaliert) + len(sup_entschieden))) if (eskaliert or sup_entschieden) else None
    einwaende = 0
    if adr_dir.exists():
        for p in adr_dir.glob("[0-9]*.md"):
            if "## Einwand des Supervisors" in text_of(p):
                einwaende += 1

    # ---- audits
    audit_dir = project / ".keel" / "work" / "audit"
    audits = []
    if audit_dir.exists():
        for p in audit_dir.glob("*.md"):
            data = fields(p)
            body = text_of(p)
            n = len(re.findall(r"^- .+ – .+ – wird (Aufgabe|Vorlage)", body, flags=re.M))
            audits.append((data, n))
    audit_avg = round(sum(n for _, n in audits) / len(audits), 1) if audits else None

    # ---- per model: outcomes of the runs each model did; review results count for the developer's model
    per_model = defaultdict(lambda: {"laeufe": 0, "rollen": set(), "blockiert": 0, "budget": 0, "tokens": 0, "reviews": 0, "befunde": 0, "runden": []})
    runs = model_runs(evs)
    model_of_agent = {r["agent_id"]: r["model"] for r in runs}
    dev_model = {}
    for r in runs:
        m = per_model[r["model"]]
        m["laeufe"] += 1
        m["rollen"].add(r["role"])
        m["budget"] += r["result"] == "budget-erschoepft"
        if r["transcript"]:
            m["tokens"] += token_usage(r["transcript"])[0]
        if r["role"] == "entwickler" and r["ref"]:
            dev_model[r["ref"]] = r["model"]
    for e in blocked:
        if e.get("agent_id") in model_of_agent:
            per_model[model_of_agent[e["agent_id"]]]["blockiert"] += 1
    for r in reviews:
        mdl = dev_model.get(r.get("aufgabe"))
        if mdl:
            per_model[mdl]["reviews"] += 1
            per_model[mdl]["befunde"] += r.get("status") == "befunde"
    for ref, n in rounds.items():
        if ref in dev_model:
            per_model[dev_model[ref]]["runden"].append(n)
    modelle = []
    for name, m in sorted(per_model.items()):
        modelle.append({
            "modell": name,
            "rollenlaeufe": m["laeufe"],
            "rollen": sorted(m["rollen"]),
            "blockierte_uebergaben_prozent": round(100 * m["blockiert"] / m["laeufe"]) if m["laeufe"] else None,
            "budget_erschoepft": m["budget"],
            "tokens_pro_lauf_k": round(m["tokens"] / m["laeufe"] / 1000, 1) if m["laeufe"] else None,
            "ruecklaufquote_review_prozent": round(100 * m["befunde"] / m["reviews"]) if m["reviews"] else None,
            "review_runden_pro_aufgabe": round(sum(m["runden"]) / len(m["runden"]), 2) if m["runden"] else None,
        })

    rows = [
        ("Meine Aufmerksamkeit", "vorlagen_pro_woche", "Vorlagen an den Menschen pro Woche", vorlagen_pro_woche),
        ("Meine Aufmerksamkeit", "entscheidungsdauer_tage", "Zeit bis zur Entscheidung (Tage)", entscheidungsdauer),
        ("PO-Kalibrierung", "gekippte_delegierte_adrs_prozent", "Gekippte delegierte ADRs (%)", gekippt_prozent),
        ("Supervisor", "gekippte_supervisor_entscheidungen_prozent", "Gekippte Supervisor-Entscheidungen (%)", sup_gekippt_prozent),
        ("Supervisor", "eskalationsquote_prozent", "Eskalationsquote an den Menschen (%)", eskalationsquote),
        ("Supervisor", "einwaende_supervisor", "Einwände des Supervisors gegen Entscheidungen des Menschen", einwaende),
        ("Planung", "diff_zeilen_pro_aufgabe", "Diff-Zeilen pro Aufgabe (Ø)", diff_avg),
        ("Planung", "neuschnitt_quote_prozent", "Neu geschnittene Aufgaben (%)", round(100 * len(neuschnitt) / len(tasks)) if tasks else None),
        ("Umsetzung", "review_runden_pro_aufgabe", "Review-Runden pro Aufgabe (Ø)", review_rounds),
        ("Umsetzung", "ruecklaufquote_review_prozent", "Reviews mit Befunden (%)", round(100 * len(befunde) / len(reviews)) if reviews else None),
        ("Umsetzung", "fix_befunde_prozent", "Nacharbeitsrunden mit neuen Befunden aus der Nacharbeit (%)", fix_prozent),
        ("Pflege", "pflege_verfallen_prozent", "Verfallene Pflege-Anmerkungen (% der erledigten)", pflege_verfallen),
        ("Übergaben", "blockierte_uebergaben_prozent", "Blockierte Übergaben (% der Rollenläufe)", round(100 * len(blocked) / len(stops)) if stops else None),
        ("Budget", "budget_verstoesse", "Budgetverstöße", len(budget)),
        ("Kontext", "kontext_alarme", "Kontext-Alarme beim Lead", len(context_alarms)),
        ("Drift", "audit_abweichungen_pro_bericht", "Audit-Abweichungen pro Bericht (Ø)", audit_avg),
        ("Kosten", "tokens_pro_aufgabe_k", "Ausgabe-Tokens pro Aufgabe (k, Ø über Rollen)", tokens_per_task),
    ]
    report = []
    violations = 0
    for area, key, label, value in rows:
        corridor = corridors.get(key)
        ok = in_corridor(value, corridor)
        if ok is False:
            violations += 1
        report.append({"bereich": area, "kennzahl": key, "label": label, "wert": value, "korridor": corridor, "status": "n/a" if ok is None else ("ok" if ok else "verletzt")})
    summary = {"projekt": project.name, "uebersprungene_ereignisse": read.skipped, "seit": text[:10] if since else None, "rollenlaeufe": len(stops), "aufgaben": len(tasks), "verletzungen": violations, "kennzahlen": report, "modelle": modelle, "offene_modellwechsel": model_switches(project)}
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"# Kennzahlen {project.name}" + (f" seit {summary['seit']}" if since else ""))
    print(f"\nRollenläufe: {len(stops)}, Aufgaben: {len(tasks)}, Korridorverletzungen: {violations}\n")
    print("| Bereich | Kennzahl | Wert | Korridor | Status |\n| --- | --- | --- | --- | --- |")
    for r in report:
        v = "–" if r["wert"] is None else r["wert"]
        print(f"| {r['bereich']} | {r['label']} | {v} | {r['korridor'] or '–'} | {r['status']} |")
    if modelle:
        dash = lambda x: "–" if x is None else x  # noqa: E731
        print("\n## Je Modell\n")
        print("| Modell | Rollenläufe | Rollen | Blockierte Übergaben (%) | Budget erschöpft | Ausgabe-Tokens pro Lauf (k) | Reviews mit Befunden (%) | Review-Runden (Ø) |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for m in modelle:
            print(f"| {m['modell']} | {m['rollenlaeufe']} | {', '.join(m['rollen'])} | {dash(m['blockierte_uebergaben_prozent'])} | {m['budget_erschoepft']} | {dash(m['tokens_pro_lauf_k'])} | {dash(m['ruecklaufquote_review_prozent'])} | {dash(m['review_runden_pro_aufgabe'])} |")
    for sw in summary["offene_modellwechsel"]:
        print(f"\nOffener Modellwechsel: {sw['modell']} seit {sw['seit']} (vorher {', '.join(sw['vorher'])}; Rollen: {', '.join(sw['rollen'])}; {sw['laeufe']} Läufe). Der Coach setzt modell_geprueft im Bericht.")
    sys.exit(3 if violations else 0)


if __name__ == "__main__":
    main()
