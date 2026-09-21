#!/usr/bin/env python3
"""keel metrics: derive the learning-loop numbers from artifacts and raw hook data.

Usage: metrics.py <project-dir> [--since YYYY-MM-DD] [--json]

Sources: ~/.keel-metrics/<project>/events.jsonl (role starts/stops, blocked stops, budgets),
subagent transcripts (tokens), git log (task diffs), .keel/work (tasks, reviews, audits),
.keel/decisions and .keel/adr. Corridors come from .keel/config.yaml under `korridore`.
Working roles never call this; it is for the human and the Coach.
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import read as read_config  # noqa: E402
from frontmatter import parse as parse_fm  # noqa: E402

DEFAULT_CORRIDORS = {
    "vorlagen_pro_woche": "2-5",
    "entscheidungsdauer_tage": "0-2",
    "gekippte_delegierte_adrs_prozent": "0-10",
    "gekippte_supervisor_entscheidungen_prozent": "0-15",
    "eskalationsquote_prozent": "10-40",
    "einwaende_supervisor": "1-10",
    "review_runden_pro_aufgabe": "1-2",
    "ruecklaufquote_review_prozent": "0-30",
    "neuschnitt_quote_prozent": "0-20",
    "blockierte_uebergaben_prozent": "0-20",
    "budget_verstoesse": "0-0",
    "kontext_alarme": "0-0",
    "audit_abweichungen_pro_bericht": "0-3",
    "diff_zeilen_pro_aufgabe": "20-300",
    "tokens_pro_aufgabe_k": "0-400",
}


def fm(path):
    data, _ = parse_fm(Path(path).read_text(encoding="utf-8"))
    return data or {}


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
        for line in Path(transcript).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") != "assistant":
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
    since = None
    if "--since" in sys.argv:
        since = datetime.fromisoformat(sys.argv[sys.argv.index("--since") + 1])
    as_json = "--json" in sys.argv
    metrics_dir = Path(os.environ.get("KEEL_METRICS_DIR", Path.home() / ".keel-metrics")) / project.name
    cfg = read_config(project / ".keel" / "config.yaml") if (project / ".keel" / "config.yaml").exists() else {}
    corridors = dict(DEFAULT_CORRIDORS)
    if isinstance(cfg.get("korridore"), dict):
        corridors.update(cfg["korridore"])

    # ---- events
    events = []
    ev_file = metrics_dir / "events.jsonl"
    if ev_file.exists():
        for line in ev_file.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = datetime.fromisoformat(e["ts"].replace("Z", ""))
            if since and ts < since:
                continue
            events.append(e)
    stops = [e for e in events if e["event"] == "agent_stop"]
    blocked = [e for e in events if e["event"] == "stop_blocked"]
    budget = [e for e in events if e["event"] == "budget_exhausted"]
    context_alarms = [e for e in events if e["event"] == "context_alarm"]

    # ---- tokens per task from subagent transcripts
    tokens_by_ref = defaultdict(int)
    for e in stops:
        if e.get("transcript"):
            out, _ = token_usage(e["transcript"])
            tokens_by_ref[e.get("ref") or "?"] += out
    task_refs = [r for r in tokens_by_ref if re.match(r"^[A-Z]+\d*-T\d+$", r)]
    tokens_per_task = round(sum(tokens_by_ref[r] for r in task_refs) / len(task_refs) / 1000, 1) if task_refs else None

    # ---- tasks and reviews
    tasks_dir = project / ".keel" / "work" / "tasks"
    tasks = {p.stem: fm(p) for p in tasks_dir.glob("*.md")} if tasks_dir.exists() else {}
    if since:
        tasks = {k: v for k, v in tasks.items() if True}  # task files carry no date; keep all
    done = [t for t in tasks.values() if t.get("status") in ("fertig", "verworfen", "ersetzt")]
    neuschnitt = [t for t in tasks.values() if int(t.get("neuschnitt_runden") or 0) > 0]
    reviews_dir = project / ".keel" / "work" / "reviews"
    reviews = [fm(p) for p in reviews_dir.glob("*.md")] if reviews_dir.exists() else []
    rounds = defaultdict(int)
    for r in reviews:
        rounds[r.get("aufgabe")] = max(rounds[r.get("aufgabe")], int(r.get("runde") or 0))
    review_rounds = round(sum(rounds.values()) / len(rounds), 2) if rounds else None
    befunde = [r for r in reviews if r.get("status") == "befunde"]

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
    done_dec = [fm(p) for p in (dec / "done").glob("*.md")] if (dec / "done").exists() else []
    all_dec = [fm(p) for p in pending] + done_dec
    weeks = 1.0
    if all_dec:
        dates = sorted(d for d in (x.get("datum") for x in all_dec) if d)
        if len(dates) >= 2:
            span = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days
            weeks = max(1.0, span / 7)
    vorlagen_pro_woche = round(len(all_dec) / weeks, 1)
    durations = []
    for d in done_dec:
        if d.get("datum") and d.get("entschieden"):
            durations.append((date.fromisoformat(d["entschieden"]) - date.fromisoformat(d["datum"])).days)
    entscheidungsdauer = round(sum(durations) / len(durations), 1) if durations else None

    # ---- ADRs
    adr_dir = project / ".keel" / "adr"
    adrs = [fm(p) for p in adr_dir.glob("[0-9]*.md") if p.stem != "0000-vorlage"] if adr_dir.exists() else []
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
            if "## Einwand des Supervisors" in p.read_text(encoding="utf-8"):
                einwaende += 1

    # ---- audits
    audit_dir = project / ".keel" / "work" / "audit"
    audits = []
    if audit_dir.exists():
        for p in audit_dir.glob("*.md"):
            data = fm(p)
            body = p.read_text(encoding="utf-8")
            n = len(re.findall(r"^- .+ – .+ – wird (Aufgabe|Vorlage)", body, flags=re.M))
            audits.append((data, n))
    audit_avg = round(sum(n for _, n in audits) / len(audits), 1) if audits else None

    rows = [
        ("Meine Aufmerksamkeit", "vorlagen_pro_woche", "Vorlagen pro Woche", vorlagen_pro_woche),
        ("Meine Aufmerksamkeit", "entscheidungsdauer_tage", "Zeit bis zur Entscheidung (Tage)", entscheidungsdauer),
        ("PO-Kalibrierung", "gekippte_delegierte_adrs_prozent", "Gekippte delegierte ADRs (%)", gekippt_prozent),
        ("Supervisor", "gekippte_supervisor_entscheidungen_prozent", "Gekippte Supervisor-Entscheidungen (%)", sup_gekippt_prozent),
        ("Supervisor", "eskalationsquote_prozent", "Eskalationsquote an den Menschen (%)", eskalationsquote),
        ("Supervisor", "einwaende_supervisor", "Einwände des Supervisors gegen Entscheidungen des Menschen", einwaende),
        ("Planung", "diff_zeilen_pro_aufgabe", "Diff-Zeilen pro Aufgabe (Ø)", diff_avg),
        ("Planung", "neuschnitt_quote_prozent", "Neu geschnittene Aufgaben (%)", round(100 * len(neuschnitt) / len(tasks)) if tasks else None),
        ("Umsetzung", "review_runden_pro_aufgabe", "Review-Runden pro Aufgabe (Ø)", review_rounds),
        ("Umsetzung", "ruecklaufquote_review_prozent", "Reviews mit Befunden (%)", round(100 * len(befunde) / len(reviews)) if reviews else None),
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
    summary = {"projekt": project.name, "seit": since.date().isoformat() if since else None, "rollenlaeufe": len(stops), "aufgaben": len(tasks), "verletzungen": violations, "kennzahlen": report}
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"# Kennzahlen {project.name}" + (f" seit {summary['seit']}" if since else ""))
    print(f"\nRollenläufe: {len(stops)}, Aufgaben: {len(tasks)}, Korridorverletzungen: {violations}\n")
    print("| Bereich | Kennzahl | Wert | Korridor | Status |\n| --- | --- | --- | --- | --- |")
    for r in report:
        v = "–" if r["wert"] is None else r["wert"]
        print(f"| {r['bereich']} | {r['label']} | {v} | {r['korridor'] or '–'} | {r['status']} |")
    sys.exit(3 if violations else 0)


if __name__ == "__main__":
    main()
