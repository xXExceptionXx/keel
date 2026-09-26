#!/usr/bin/env python3
"""Situation report for the helper skill (/keel:hilfe): what the system is doing, derived from state.

Usage: lage.py <project-dir> [--hours N] [--plugin-root DIR] [--json] [--clean]

Sections: project and plugin versions, due items, open Vorhaben and epics, open Vorlagen,
events of the last N hours grouped by kind and reason, leftover state files.
--clean removes leftover state files (stale pending markers, per-agent files of finished runs,
context step markers older than a day). Reads only; never touches .keel/ content.
"""
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import read as read_config  # noqa: E402
from frontmatter import parse as parse_fm  # noqa: E402

ACTIVE_PLAN = {"integriert", "verworfen", "abgeschlossen"}
STALE_AGENT_SECONDS = 24 * 3600
STALE_PENDING_SECONDS = 600


def fm(p):
    try:
        d, _ = parse_fm(p.read_text(encoding="utf-8"))
    except OSError:
        return {}
    return d or {}


def sh(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else default
    return default


def plugin_versions(project, plugin_root):
    """Version in use (plugin root), installed for this project, and offered by the marketplace."""
    out = {"genutzt": None, "installiert": None, "marketplace": None}
    if plugin_root:
        pj = Path(plugin_root) / ".claude-plugin" / "plugin.json"
        if pj.exists():
            try:
                out["genutzt"] = json.loads(pj.read_text(encoding="utf-8")).get("version")
            except ValueError:
                pass
    home = Path.home() / ".claude" / "plugins"
    reg = home / "installed_plugins.json"
    if reg.exists():
        try:
            entries = json.loads(reg.read_text(encoding="utf-8")).get("plugins", {}).get("keel@keel", [])
        except ValueError:
            entries = []
        for e in entries:
            if e.get("projectPath") == str(project) or e.get("scope") == "user":
                out["installiert"] = e.get("version")
                break
    mp = home / "marketplaces" / "keel" / ".claude-plugin" / "marketplace.json"
    if mp.exists():
        try:
            for p in json.loads(mp.read_text(encoding="utf-8")).get("plugins", []):
                if p.get("name") == "keel":
                    out["marketplace"] = p.get("version")
        except ValueError:
            pass
    return out


def due(project):
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "due.py"), str(project), "--json"], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"hart": False, "faellig": []}


def vorhaben(project):
    plans = project / ".keel" / "work" / "plans"
    tasks = project / ".keel" / "work" / "tasks"
    out = []
    if not plans.exists():
        return out
    for p in sorted(plans.glob("*.md")):
        d = fm(p)
        if d.get("typ") != "plan" or d.get("status") in ACTIVE_PLAN:
            continue
        name = p.stem
        counts = Counter()
        vid = d.get("vorhaben")
        if tasks.exists() and vid:
            for t in tasks.glob("*.md"):
                td = fm(t)
                if td.get("vorhaben") == vid:
                    counts[td.get("status", "?")] += 1
        out.append({"name": name, "id": vid, "status": d.get("status"), "branch": d.get("branch"), "epic": d.get("epic"), "aufgaben": dict(counts)})
    return out


def epics(project):
    ep = project / ".keel" / "work" / "epics"
    out = []
    if not ep.exists():
        return out
    for p in sorted(ep.glob("*.md")):
        if p.name.endswith(".bewertung.md"):
            continue
        d = fm(p)
        out.append({"name": p.stem, "status": d.get("status")})
    return out


def vorlagen(project):
    pend = project / ".keel" / "decisions" / "pending"
    out = []
    if not pend.exists():
        return out
    today = date.today()
    for p in sorted(pend.glob("*.md")):
        d = fm(p)
        try:
            age = (today - date.fromisoformat(str(d.get("datum")))).days
        except (TypeError, ValueError):
            age = None
        out.append({"datei": str(p.relative_to(project)), "titel": d.get("titel"), "von": d.get("von"), "eskaliert": d.get("eskaliert"), "alter_tage": age})
    return out


def reason_key(e):
    """Group reasons that differ only in numbers ("hat 4 Zeilen" and "hat 9 Zeilen")."""
    return re.sub(r"\d+", "N", str(e.get("reason", "")))[:90]


def events(metrics_dir, hours):
    """Events of the last N hours from events.jsonl, grouped."""
    f = metrics_dir / "events.jsonl"
    since = time.time() - hours * 3600
    runs = Counter()
    blocked = defaultdict(Counter)
    budget = Counter()
    denied = defaultdict(Counter)
    alarms = 0
    stops = {}
    starts = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
                ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).timestamp()
            except (ValueError, KeyError):
                continue
            ev = e.get("event")
            if ev == "agent_start":
                starts[e.get("agent_id")] = e
            if ev == "agent_stop":
                stops[e.get("agent_id")] = e
            if ts < since:
                continue
            if ev == "agent_stop":
                runs[f"{e.get('role')}:{e.get('result')}"] += 1
            elif ev == "stop_blocked":
                blocked[e.get("role")][reason_key(e)] += 1
            elif ev == "budget_exhausted":
                budget[e.get("role")] += 1
            elif ev == "denied":
                denied[e.get("hook")][reason_key(e)] += 1
            elif ev == "context_alarm":
                alarms += 1
    return {
        "rollenlaeufe": dict(runs),
        "blockierte_uebergaben": {r: dict(c) for r, c in blocked.items()},
        "budget_erschoepft": dict(budget),
        "ablehnungen": {h: dict(c) for h, c in denied.items()},
        "kontext_alarme": alarms,
        "_starts": starts,
        "_stops": stops,
    }


def state_files(state_dir, starts, stops):
    """Leftover state: pending markers, per-agent files, context markers. Returns findings and cleanup candidates."""
    now = time.time()
    findings = []
    cleanup = []
    if not state_dir.exists():
        return findings, cleanup
    for p in state_dir.glob("pending-*"):
        age = now - p.stat().st_mtime
        role = p.name[len("pending-"):]
        if age > STALE_PENDING_SECONDS:
            findings.append(f"pending-{role}: geparkte Referenz seit {int(age // 60)} Minuten ohne Start der Rolle (Start abgebrochen?)")
            cleanup.append(p)
        else:
            findings.append(f"pending-{role}: Rolle startet gerade ({int(age)} s)")
    agents = defaultdict(list)
    for p in state_dir.glob("agent-*.*"):
        agents[p.name.split(".")[0][len("agent-"):]].append(p)
    running, stale, finished = [], 0, 0
    for aid, files in agents.items():
        start_f = state_dir / f"agent-{aid}.start"
        try:
            started = int(start_f.read_text().strip()) if start_f.exists() else None
        except ValueError:
            started = None
        age = now - started if started else None
        if aid in stops or age is None or age > STALE_AGENT_SECONDS:
            if aid in stops:
                finished += 1
            else:
                stale += 1
            cleanup.extend(files)
        else:
            role = (state_dir / f"agent-{aid}.role").read_text().strip() if (state_dir / f"agent-{aid}.role").exists() else "?"
            ref = (state_dir / f"agent-{aid}.ref").read_text().strip() if (state_dir / f"agent-{aid}.ref").exists() else ""
            running.append(f"{role} {ref} seit {int(age // 60)} Minuten (kein Stopp-Ereignis)")
    if running:
        findings.append("Läuft oder liegengeblieben: " + "; ".join(running))
    if finished or stale:
        findings.append(f"Reste beendeter Läufe: {finished} mit Stopp-Ereignis, {stale} ohne (älter als ein Tag). Aufräumen mit --clean.")
    for p in state_dir.glob("context-*.step"):
        if now - p.stat().st_mtime > STALE_AGENT_SECONDS:
            cleanup.append(p)
    return findings, cleanup


def newest_dated(dirpath):
    if not dirpath.exists():
        return None
    best = None
    for p in dirpath.glob("*.md"):
        d = fm(p)
        if d.get("datum") and (best is None or str(d["datum"]) > str(best[0])):
            best = (d["datum"], p.name, d.get("status"))
    return best


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    hours = int(arg("--hours", "24"))
    plugin_root = arg("--plugin-root") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    cfg_path = project / ".keel" / "config.yaml"
    cfg = read_config(cfg_path) if cfg_path.exists() else {}
    metrics_dir = Path(os.environ.get("KEEL_METRICS_DIR", Path.home() / ".keel-metrics")) / project.name
    state_dir = metrics_dir / "state"

    ev = events(metrics_dir, hours)
    findings, cleanup = state_files(state_dir, ev.pop("_starts"), ev.pop("_stops"))

    if "--clean" in sys.argv:
        n = 0
        for p in cleanup:
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
        print(f"{n} Zustandsdateien entfernt")
        sys.exit(0)

    report = {
        "projekt": project.name,
        "branch": sh(["git", "branch", "--show-current"], project),
        "basis": (cfg.get("git") or {}).get("base_branch") if isinstance(cfg.get("git"), dict) else None,
        "arbeitsbaum_geaendert": len([l for l in sh(["git", "status", "--porcelain"], project).splitlines() if l]),
        "plugin": plugin_versions(project, plugin_root),
        "faellig": due(project),
        "vorhaben": vorhaben(project),
        "epics": epics(project),
        "vorlagen": vorlagen(project),
        "ereignisse": ev,
        "ereignisse_stunden": hours,
        "zustandsdateien": findings,
        "letzte_uebergabe": newest_dated(project / ".keel" / "work" / "handoff"),
        "letzter_pruefbericht": newest_dated(project / ".keel" / "work" / "audit"),
    }

    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return

    pv = report["plugin"]
    print(f"Projekt {report['projekt']}, Branch {report['branch'] or '?'} (Basis {report['basis'] or '?'}), "
          f"{report['arbeitsbaum_geaendert']} geänderte Dateien im Arbeitsbaum")
    ver = f"Plugin: genutzt {pv['genutzt'] or '?'}, installiert {pv['installiert'] or '?'}, Marketplace {pv['marketplace'] or '?'}"
    if pv["installiert"] and pv["marketplace"] and pv["installiert"] != pv["marketplace"]:
        ver += "  ← Update ausstehend: claude plugin update keel@keel --scope project"
    print(ver)

    print("\nFällig:")
    if not report["faellig"]["faellig"]:
        print("  nichts")
    for i in report["faellig"]["faellig"]:
        print(f"  {'HART' if i['hart'] else 'soft'}  {i['art']}: {i['grund']} → {i['befehl']}")

    print("\nVorhaben und Epics:")
    for e in report["epics"]:
        print(f"  Epic {e['name']}: {e['status']}")
    for v in report["vorhaben"]:
        tasks = ", ".join(f"{k} {n}" for k, n in sorted(v["aufgaben"].items())) or "keine Aufgaben"
        print(f"  {v['name']}: {v['status']}" + (f" auf {v['branch']}" if v.get("branch") else "") + f" ({tasks})")
    if not report["epics"] and not report["vorhaben"]:
        print("  keine offenen")

    print("\nOffene Vorlagen:")
    if not report["vorlagen"]:
        print("  keine")
    for v in report["vorlagen"]:
        tag = "richtungsweisend, wartet auf dich im Briefing" if v["eskaliert"] else "entscheidet der Supervisor beim nächsten Start"
        print(f"  {v['titel'] or v['datei']} (von {v['von'] or '?'}, {v['alter_tage']} Tage alt): {tag}")

    print(f"\nEreignisse der letzten {hours} Stunden:")
    e = report["ereignisse"]
    print("  Rollenläufe: " + (", ".join(f"{k} {n}" for k, n in sorted(e["rollenlaeufe"].items())) or "keine"))
    if e["blockierte_uebergaben"]:
        for role, reasons in e["blockierte_uebergaben"].items():
            for reason, n in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"  blockierte Übergabe {role} ×{n}: {reason}")
    if e["budget_erschoepft"]:
        print("  Budget erschöpft: " + ", ".join(f"{k} {n}" for k, n in e["budget_erschoepft"].items()))
    if e["ablehnungen"]:
        for hook, reasons in e["ablehnungen"].items():
            for reason, n in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"  Ablehnung {hook} ×{n}: {reason}")
    if e["kontext_alarme"]:
        print(f"  Kontext-Alarme: {e['kontext_alarme']}")

    print("\nZustandsdateien:")
    for f in report["zustandsdateien"] or ["sauber"]:
        print(f"  {f}")

    lu, lp = report["letzte_uebergabe"], report["letzter_pruefbericht"]
    print(f"\nLetzte Übergabenotiz: {lu[0] if lu else 'keine'}; letzter Prüfbericht: {lp[0] + ' (' + str(lp[2]) + ')' if lp else 'keiner'}")


if __name__ == "__main__":
    main()
