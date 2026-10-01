#!/usr/bin/env python3
"""Situation report for the helper skill (/keel:hilfe): what the system is doing, derived from state.

Usage: lage.py <project-dir> [--hours N] [--plugin-root DIR] [--json] [--clean]

Sections: project and plugin versions, due items, health (keel doctor), open Vorhaben and epics, open Vorlagen,
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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import KeelError
from keel.services import doctor
from keel.store import config, events
from keel.store.frontmatter import fields_tolerant as fields
from keel.store.paths import Paths

ACTIVE_PLAN = {"integriert", "verworfen", "abgeschlossen"}
STALE_AGENT_SECONDS = 24 * 3600
STALE_PENDING_SECONDS = doctor.STALE_PENDING_SECONDS


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
        if r.returncode in (0, 1):
            return json.loads(r.stdout)
    except ValueError:
        pass
    # due.py could not tell (exit 2 or unreadable output): say so instead of reporting "nothing due" (System-ADR 0019)
    grund = (r.stderr.strip().splitlines() or [f"due.py endete mit {r.returncode}"])[-1]
    return {"hart": True, "fehler": grund, "faellig": [{"art": "fehler", "hart": True, "rolle": "", "grund": f"Fälligkeiten nicht prüfbar: {grund}", "befehl": "/keel:hilfe"}]}


def vorhaben(project):
    plans = project / ".keel" / "work" / "plans"
    tasks = project / ".keel" / "work" / "tasks"
    out = []
    if not plans.exists():
        return out
    for p in sorted(plans.glob("*.md")):
        d = fields(p)
        if d.get("typ") != "plan" or d.get("status") in ACTIVE_PLAN:
            continue
        name = p.stem
        counts = Counter()
        vid = d.get("vorhaben")
        if tasks.exists() and vid:
            for t in tasks.glob("*.md"):
                td = fields(t)
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
        d = fields(p)
        out.append({"name": p.stem, "status": d.get("status")})
    return out


def vorlagen(project):
    pend = project / ".keel" / "decisions" / "pending"
    out = []
    if not pend.exists():
        return out
    today = date.today()
    for p in sorted(pend.glob("*.md")):
        d = fields(p)
        try:
            age = (today - date.fromisoformat(str(d.get("datum")))).days
        except (TypeError, ValueError):
            age = None
        out.append({"datei": str(p.relative_to(project)), "titel": d.get("titel"), "von": d.get("von"), "eskaliert": d.get("eskaliert"), "alter_tage": age})
    return out


def reason_key(e):
    """Group reasons that differ only in numbers ("hat 4 Zeilen" and "hat 9 Zeilen")."""
    return re.sub(r"\d+", "N", str(e.get("reason", "")))[:90]


def grouped_events(paths, hours):
    """Events of the last N hours, grouped; starts and stops of all time for the per-agent state."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    runs = Counter()
    blocked = defaultdict(Counter)
    budget = Counter()
    denied = defaultdict(Counter)
    alarms = 0
    stops = {}
    starts = {}
    for e in events.read(paths.events).events:
        ev = e.get("event")
        if ev == "agent_start":
            starts[e.get("agent_id")] = e
        if ev == "agent_stop":
            stops[e.get("agent_id")] = e
        if e["_ts"] < since:
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


def read_text(p):
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def agent_runs(state_dir, stops, now=None):
    """Per-agent state files grouped by agent id. zustand: laeuft (no stop event, younger than a day),
    beendet (stop event recorded) or liegengeblieben (no stop event, older than a day or no start time)."""
    now = now or time.time()
    agents = defaultdict(list)
    if state_dir.exists():
        for p in state_dir.glob("agent-*.*"):
            agents[p.name.split(".")[0][len("agent-"):]].append(p)
    out = []
    for aid, files in agents.items():
        try:
            started = int(read_text(state_dir / f"agent-{aid}.start"))
        except ValueError:
            started = None
        age = int(now - started) if started else None
        if aid in stops:
            zustand = "beendet"
        elif age is None or age > STALE_AGENT_SECONDS:
            zustand = "liegengeblieben"
        else:
            zustand = "laeuft"
        out.append({
            "agent_id": aid,
            "rolle": read_text(state_dir / f"agent-{aid}.role") or "?",
            "ref": read_text(state_dir / f"agent-{aid}.ref"),
            "start": started,
            "seit_sekunden": age,
            "werkzeugaufrufe": read_text(state_dir / f"agent-{aid}.calls") or None,
            "zeitbudget_erschoepft": (state_dir / f"agent-{aid}.timeout").exists(),
            "zustand": zustand,
            "_files": files,
        })
    return out


def state_files(state_dir, starts, stops):
    """Leftover state: pending markers, per-agent files, context markers. Returns findings and cleanup candidates."""
    now = time.time()
    findings = []
    cleanup = []
    if not state_dir.exists():
        return findings, cleanup
    brake = state_dir / "kern-gesperrt"
    if brake.exists():
        # never cleaned up automatically: the human fixes the cause and removes the lock (System-ADR 0019)
        text = brake.read_text(encoding="utf-8", errors="replace").strip()
        findings.append(f"NOTBREMSE, alle Rollen gesperrt: {text}")
    for p in state_dir.glob("pending-*"):
        age = now - p.stat().st_mtime
        role = p.name[len("pending-"):]
        if age > STALE_PENDING_SECONDS:
            findings.append(f"pending-{role}: geparkte Referenz seit {int(age // 60)} Minuten ohne Start der Rolle (Start abgebrochen?)")
            cleanup.append(p)
        else:
            findings.append(f"pending-{role}: Rolle startet gerade ({int(age)} s)")
    running, stale, finished = [], 0, 0
    for a in agent_runs(state_dir, stops, now):
        if a["zustand"] == "laeuft":
            running.append(f"{a['rolle']} {a['ref']} seit {a['seit_sekunden'] // 60} Minuten (kein Stopp-Ereignis)")
            continue
        if a["zustand"] == "beendet":
            finished += 1
        else:
            stale += 1
        cleanup.extend(a["_files"])
    if running:
        findings.append("Läuft oder liegengeblieben: " + "; ".join(running))
    if finished or stale:
        findings.append(f"Reste beendeter Läufe: {finished} mit Stopp-Ereignis, {stale} ohne (älter als ein Tag). Aufräumen mit --clean.")
    for p in list(state_dir.glob("context-*.step")) + list(state_dir.glob("hilfe-*")):
        if now - p.stat().st_mtime > STALE_AGENT_SECONDS:
            cleanup.append(p)
    return findings, cleanup


def newest_dated(dirpath):
    if not dirpath.exists():
        return None
    best = None
    for p in dirpath.glob("*.md"):
        d = fields(p)
        if d.get("datum") and (best is None or str(d["datum"]) > str(best[0])):
            best = (d["datum"], p.name, d.get("status"))
    return best


_health = {}
HEALTH_TTL = 60.0


def health(project, fast):
    """Findings of keel doctor that are not ok. fast (the monitor, polled every few seconds): without starting
    git and jq, and reused for HEALTH_TTL seconds."""
    if not fast:
        return [f.as_dict() for f in doctor.run(project) if f.stufe != doctor.OK]
    hit = _health.get(str(project))
    if not hit or time.time() - hit[0] > HEALTH_TTL:
        hit = (time.time(), [f.as_dict() for f in doctor.run(project, tools=False) if f.stufe != doctor.OK])
        _health[str(project)] = hit
    return hit[1]


def build_report(project, hours=24, plugin_root=None, fast=False):
    """The situation report as a dict, plus the state files --clean would remove. Shared with monitor.py."""
    paths = Paths(project)
    try:
        cfg = config.load_file(paths.config)
    except KeelError:
        cfg = {}  # reported by the health section

    ev = grouped_events(paths, hours)
    findings, cleanup = state_files(paths.state, ev.pop("_starts"), ev.pop("_stops"))

    report = {
        "projekt": project.name,
        "branch": sh(["git", "branch", "--show-current"], project),
        "basis": config.get(cfg, "git.base_branch"),
        "arbeitsbaum_geaendert": len([l for l in sh(["git", "status", "--porcelain"], project).splitlines() if l]),
        "plugin": plugin_versions(project, plugin_root),
        "faellig": due(project),
        "gesundheit": health(project, fast),
        "vorhaben": vorhaben(project),
        "epics": epics(project),
        "vorlagen": vorlagen(project),
        "ereignisse": ev,
        "ereignisse_stunden": hours,
        "zustandsdateien": findings,
        "letzte_uebergabe": newest_dated(project / ".keel" / "work" / "handoff"),
        "letzter_pruefbericht": newest_dated(project / ".keel" / "work" / "audit"),
    }
    return report, cleanup


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    hours = int(arg("--hours", "24"))
    plugin_root = arg("--plugin-root") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    report, cleanup = build_report(project, hours, plugin_root)

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

    print("\nGesundheit (keel doctor):")
    if not report["gesundheit"]:
        print("  alles in Ordnung")
    for f in report["gesundheit"]:
        print(f"  {f['stufe'].upper()}  {f['pruefung']}: {f['meldung']}")

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
