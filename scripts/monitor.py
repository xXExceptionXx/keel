#!/usr/bin/env python3
"""Flow monitor: a local web page that shows what keel is doing, with the handoffs as documentation.

Usage: monitor.py [project-dir] [--port N] [--plugin-root DIR] [--hours N]
       monitor.py [project-dir] --ensure [--if-autostart] [--quiet]
       monitor.py [project-dir] --stop

Serves one page on http://127.0.0.1:<port>/ and a small JSON API. The port comes from --port, else
monitor.port in .keel/config.yaml, else 8765.
  /api/state            situation report (lage.py), running role with its calling command, recent events
  /api/vorhaben         all Vorhaben with status; ?name=<plan> one Vorhaben as a timeline
  /api/files            the Markdown files under .keel/ with their frontmatter, grouped by folder
  /api/file?path=...    one file under .keel/ (frontmatter and body)
  /api/doc?name=...     a document of the motor itself (docs/system.md, docs/konzept.md, agents, skills)
  /api/ping             which project this server shows

--ensure starts the server detached unless one for this project already answers on the port, prints
the address and exits. With --if-autostart it does nothing unless monitor.autostart is true in
.keel/config.yaml; the start commands (skill-gate hook, keel.sh, keel-run.sh) call it that way.
--stop ends a monitor that --ensure started for this project.

Observer only (System-ADR 0017): reads state, events and files, writes nothing, starts nothing.
Binds to 127.0.0.1 and answers only requests addressed to localhost.
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent))
from config import read as read_config  # noqa: E402
from frontmatter import parse as parse_fm  # noqa: E402
from lage import agent_runs, build_report, metrics_dir_of  # noqa: E402

PAGE = Path(__file__).parent / "monitor.html"
EVENT_TAIL = 200            # events.jsonl lines shown in the stream
HOOKS_TAIL_BYTES = 512_000  # tail of hooks.jsonl scanned for commands and skill calls
STATE_TTL = 2.0             # seconds a computed state is reused across polls and tabs
DEFAULT_PORT = 8765

# The flow of a Vorhaben as skills/vorhaben/SKILL.md runs it: phases by plan status, and who acts next
# for a plan or task status. Mirrors the skill; the Lead still decides, this only reads the rule.
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


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else default
    return default


def tail_lines(path, max_bytes):
    """Last complete lines of a file, reading at most max_bytes from the end."""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            f.seek(max(0, size - max_bytes))
            data = f.read()
    except OSError:
        return []
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if size > max_bytes else lines


def parse_json_lines(lines):
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def commands(metrics_dir):
    """Typed /keel:<skill> prompts and Skill tool calls from the raw hook log, oldest first."""
    out = []
    for e in parse_json_lines(tail_lines(metrics_dir / "hooks.jsonl", HOOKS_TAIL_BYTES)):
        hook = e.get("hook_event_name")
        skill = None
        if hook == "UserPromptSubmit":
            prompt = str(e.get("prompt", "")).strip()
            if prompt.startswith("/keel:"):
                skill = prompt.split()[0][1:]
        elif hook == "PreToolUse" and e.get("tool_name") == "Skill" and not e.get("agent_id"):
            skill = str((e.get("tool_input") or {}).get("skill", ""))
            if skill and not skill.startswith("keel:"):
                skill = None
        if skill:
            out.append({"event": "befehl", "ts": e.get("ts"), "befehl": "/" + skill, "session_id": e.get("session_id")})
    return out


_events_cache = {}


def load_events(md):
    """All of events.jsonl, re-read only when the file changed. Callers get copies of the dicts."""
    f = md / "events.jsonl"
    try:
        st = f.stat()
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        return []
    hit = _events_cache.get(f)
    if not hit or hit[0] != key:
        hit = (key, parse_json_lines(tail_lines(f, 16_000_000)))
        _events_cache[f] = hit
    return [dict(e) for e in hit[1]]


def state(project, plugin_root, hours):
    report, _ = build_report(project, hours, plugin_root)
    md = metrics_dir_of(project)
    events = load_events(md)
    stops = {e.get("agent_id") for e in events if e.get("event") == "agent_stop"}
    starts = {e.get("agent_id"): e for e in events if e.get("event") == "agent_start"}
    cmds = commands(md)

    active = []
    for a in agent_runs(md / "state", stops):
        if a["zustand"] != "laeuft":
            continue
        a.pop("_files")
        st = starts.get(a["agent_id"], {})
        a["lead_model"] = st.get("lead_model")
        # The Lead calls every role; what matters is the command it was running at the time.
        started_at = st.get("ts") or ""
        before = [c for c in cmds if (c.get("ts") or "") <= started_at] if started_at else cmds
        a["befehl"] = before[-1]["befehl"] if before else None
        active.append(a)

    starting = []
    sd = md / "state"
    if sd.exists():
        for p in sd.glob("pending-*"):
            age = time.time() - p.stat().st_mtime
            if age < 600:
                starting.append({"rolle": p.name[len("pending-"):], "ref": p.read_text(encoding="utf-8").strip(), "seit_sekunden": int(age)})

    stream = sorted(events[-EVENT_TAIL:] + cmds[-50:], key=lambda e: e.get("ts") or "")
    for e in stream:
        e.pop("transcript", None)
    return {
        "lage": report,
        "aktiv": active,
        "startet": starting,
        "ereignisse": stream[-EVENT_TAIL:],
        "zeit": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def phase_of(status, has_tasks):
    if status == "blockiert":
        return 3 if has_tasks else 0
    for i, (_, statuses, _) in enumerate(PHASES):
        if status in statuses:
            return i
    return None


def runs_for(events, refs):
    """Role runs whose reference is one of refs: start and stop paired by agent id, with blocked
    handoffs and budget events of the same run attached. Oldest first."""
    runs = {}
    for e in events:
        aid = e.get("agent_id")
        ev = e.get("event")
        if ev == "agent_start" and e.get("ref") in refs:
            runs[aid] = {"agent_id": aid, "rolle": e.get("role"), "ref": e.get("ref"), "start": e.get("ts"),
                         "stop": None, "ergebnis": None, "werkzeugaufrufe": None, "modell": None, "vorfaelle": []}
        elif aid in runs and ev == "agent_stop":
            runs[aid].update(stop=e.get("ts"), ergebnis=e.get("result"), werkzeugaufrufe=e.get("calls"), modell=e.get("model"))
        elif aid in runs and ev in ("stop_blocked", "budget_exhausted"):
            runs[aid]["vorfaelle"].append({"art": ev, "ts": e.get("ts"), "grund": e.get("reason") or
                                           (f"{e['calls']} Werkzeugaufrufe" if e.get("calls") else f"{e.get('minutes')} Minuten")})
    return sorted(runs.values(), key=lambda r: r["start"] or "")


def vorhaben_list(project):
    plans = project / ".keel" / "work" / "plans"
    out = []
    for p in sorted(plans.glob("*.md")) if plans.exists() else []:
        d, _ = fm_of(p)
        if d.get("typ") != "plan":
            continue
        out.append({"name": p.stem, "id": d.get("vorhaben"), "status": d.get("status"), "epic": d.get("epic"),
                    "titel": d.get("titel"), "geaendert": int(p.stat().st_mtime)})
    return out


def vorhaben_detail(project, name):
    """One Vorhaben from its files and events: phase, tasks with reviews and compliance, acceptance,
    Vorlagen that name it, and the role runs in order."""
    work = project / ".keel" / "work"
    plan = work / "plans" / f"{name}.md"
    if not plan.is_file() or plan.resolve().parent != (work / "plans").resolve():
        return None
    d, _ = fm_of(plan)
    vid = d.get("vorhaben") or ""
    order = d.get("aufgaben") if isinstance(d.get("aufgaben"), list) else []
    rel = lambda p: str(p.relative_to(project))  # noqa: E731

    tasks = {}
    for t in sorted((work / "tasks").glob("*.md")) if (work / "tasks").exists() else []:
        td, _ = fm_of(t)
        if vid and td.get("vorhaben") == vid:
            tid = td.get("id") or t.stem
            reviews = []
            for r in sorted((work / "reviews").glob(f"{tid}-r*.md")) if (work / "reviews").exists() else []:
                rd, _ = fm_of(r)
                reviews.append({"pfad": rel(r), "name": r.stem, "status": rd.get("status")})
            comp = [rel(c) for c in sorted((work / "compliance").glob(f"{tid}*.md"))] if (work / "compliance").exists() else []
            tasks[tid] = {"id": tid, "pfad": rel(t), "titel": td.get("titel"), "status": td.get("status"),
                          "im_plan": tid in order, "review_runde": td.get("review_runde"),
                          "neuschnitt_runden": td.get("neuschnitt_runden"), "compliance": td.get("compliance"),
                          "reviews": reviews, "compliance_dateien": comp,
                          "naechste": NEXT_TASK.get(td.get("status"))}
    ordered = [tasks[i] for i in order if i in tasks] + [t for i, t in sorted(tasks.items()) if i not in order]

    acc = work / "acceptance" / f"{name}.md"
    acceptance = None
    if acc.is_file():
        ad, _ = fm_of(acc)
        acceptance = {"pfad": rel(acc), "status": ad.get("status")}

    keys = [k for k in [vid, name] + list(tasks) if k]
    vorlagen = []
    for sub in ("pending", "done"):
        folder = project / ".keel" / "decisions" / sub
        for v in sorted(folder.glob("*.md")) if folder.exists() else []:
            if any(k in v.stem for k in keys):
                vd, _ = fm_of(v)
                vorlagen.append({"pfad": rel(v), "titel": vd.get("titel") or v.stem, "offen": sub == "pending",
                                 "eskaliert": vd.get("eskaliert"), "entscheider": vd.get("entscheider"),
                                 "entscheidung": vd.get("entscheidung")})

    epic = d.get("epic")
    epic_path = work / "epics" / f"{epic}.md" if epic else None
    refs = {name, *tasks}
    if epic:
        refs.add(f"epic:{epic}")
    status = d.get("status")
    return {
        "name": name, "id": vid, "titel": d.get("titel"), "status": status, "branch": d.get("branch"),
        "pfad": rel(plan), "epic": epic, "epic_pfad": rel(epic_path) if epic_path and epic_path.is_file() else None,
        "phasen": [{"name": n, "zustaendig": who} for n, _, who in PHASES],
        "phase": phase_of(status, bool(tasks)),
        "naechste": NEXT_PLAN.get(status),
        "aufgaben": ordered,
        "abnahme": acceptance,
        "vorlagen": vorlagen,
        "laeufe": runs_for(load_events(metrics_dir_of(project)), refs),
    }


def keel_root(project):
    return (project / ".keel").resolve()


def fm_of(path):
    try:
        d, body = parse_fm(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}, ""
    d = {k: v for k, v in (d or {}).items() if not k.startswith("__")}
    return d, body


def files(project):
    """Markdown files under .keel/, grouped by folder, with the frontmatter fields the page shows."""
    root = keel_root(project)
    groups = {}
    if not root.exists():
        return {"gruppen": []}
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(project)
        d, _ = fm_of(p)
        folder = str(p.parent.relative_to(project))
        groups.setdefault(folder, []).append({
            "pfad": str(rel),
            "name": p.stem,
            "typ": d.get("typ"),
            "status": d.get("status"),
            "titel": d.get("titel"),
            "datum": d.get("datum"),
            "vorhaben": d.get("vorhaben"),
            "id": d.get("id"),
            "geaendert": int(p.stat().st_mtime),
        })
    return {"gruppen": [{"ordner": k, "dateien": v} for k, v in sorted(groups.items())]}


def safe_under(base, rel):
    """Resolve rel under base; None when it escapes base or is not a Markdown file."""
    try:
        p = (base / rel).resolve()
    except (OSError, ValueError):
        return None
    if base != p and base not in p.parents:
        return None
    if p.suffix != ".md" or not p.is_file():
        return None
    return p


def read_doc(path, shown):
    d, body = fm_of(path)
    return {"pfad": shown, "frontmatter": d, "body": body if d else path.read_text(encoding="utf-8", errors="replace")}


def motor_docs(plugin_root):
    root = Path(plugin_root)
    out = []
    for sub in ("docs", "agents", "skills"):
        # top-level documents (system, konzept) before the ADRs
        for p in sorted((root / sub).rglob("*.md"), key=lambda p: (len(p.relative_to(root).parts), str(p))):
            out.append(str(p.relative_to(root)))
    return out


class Handler(BaseHTTPRequestHandler):
    project = None
    plugin_root = None
    hours = 24
    _cache = (0.0, None)
    _lock = threading.Lock()

    def log_message(self, fmt, *args):  # quiet: the page polls every few seconds
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def host_ok(self):
        # Guards against DNS rebinding: a foreign page must not read the project through this server.
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        return host in ("127.0.0.1", "localhost", "::1")

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"fehler": "nur localhost"})
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/":
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/state":
                with Handler._lock:
                    ts, cached = Handler._cache
                    if cached is None or time.time() - ts > STATE_TTL:
                        cached = state(self.project, self.plugin_root, self.hours)
                        Handler._cache = (time.time(), cached)
                return self.send(200, cached)
            if url.path == "/api/ping":
                return self.send(200, {"keel_monitor": True, "projekt": str(self.project)})
            if url.path == "/api/vorhaben":
                name = (q.get("name") or [""])[0]
                if not name:
                    return self.send(200, {"vorhaben": vorhaben_list(self.project)})
                detail = vorhaben_detail(self.project, name)
                return self.send(200, detail) if detail else self.send(404, {"fehler": f"kein Vorhaben: {name}"})
            if url.path == "/api/files":
                out = files(self.project)
                out["motor"] = motor_docs(self.plugin_root)
                return self.send(200, out)
            if url.path == "/api/file":
                rel = (q.get("path") or [""])[0]
                p = safe_under(keel_root(self.project), rel[len(".keel/"):] if rel.startswith(".keel/") else rel)
                if not p:
                    return self.send(404, {"fehler": f"nicht gefunden oder außerhalb von .keel/: {rel}"})
                return self.send(200, read_doc(p, str(p.relative_to(self.project))))
            if url.path == "/api/doc":
                rel = (q.get("name") or [""])[0]
                root = Path(self.plugin_root).resolve()
                p = safe_under(root, rel)
                if not p or p.relative_to(root).parts[0] not in ("docs", "agents", "skills"):
                    return self.send(404, {"fehler": f"kein Motor-Dokument: {rel}"})
                return self.send(200, read_doc(p, "keel/" + str(p.relative_to(root))))
        except Exception as ex:  # a broken file must not take the page down
            return self.send(500, {"fehler": f"{type(ex).__name__}: {ex}"})
        return self.send(404, {"fehler": "unbekannter Pfad"})


def config_of(project):
    cfg = project / ".keel" / "config.yaml"
    try:
        return (read_config(cfg).get("monitor") or {}) if cfg.exists() else {}
    except (OSError, AttributeError):
        return {}


def ping(port):
    """The project a keel monitor on this port shows; None when nothing answers, "" for another server."""
    try:
        with urlopen(Request(f"http://127.0.0.1:{port}/api/ping"), timeout=1) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d.get("projekt", "") if d.get("keel_monitor") else ""
    except (URLError, OSError, ValueError):
        return None


def ensure(project, port, plugin_root, quiet):
    """Start the monitor detached unless it already runs for this project. Returns an exit code."""
    say = (lambda m: None) if quiet else (lambda m: print(m, flush=True))
    url = f"http://127.0.0.1:{port}/"
    running = ping(port)
    if running == str(project):
        say(f"keel-Monitor läuft: {url}")
        return 0
    if running is not None:
        print(f"keel-Monitor: Port {port} ist belegt ({running or 'anderer Dienst'}). "
              f"Setze monitor.port in .keel/config.yaml auf einen freien Port.", file=sys.stderr)
        return 1
    log_dir = metrics_dir_of(project) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "monitor.log", "ab") as log:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), str(project), "--port", str(port), "--plugin-root", plugin_root],
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, close_fds=True)
    (log_dir / "monitor.pid").write_text(f"{proc.pid} {port}\n")
    for _ in range(20):
        time.sleep(0.1)
        if ping(port) == str(project):
            say(f"keel-Monitor gestartet: {url}")
            return 0
    print(f"keel-Monitor startete nicht; siehe {log_dir / 'monitor.log'}", file=sys.stderr)
    return 1


def stop(project):
    pid_file = metrics_dir_of(project) / "logs" / "monitor.pid"
    try:
        pid, port = (int(x) for x in pid_file.read_text().split())
    except (OSError, ValueError):
        print("Kein mit --ensure gestarteter Monitor bekannt.")
        return 0
    if ping(port) != str(project):
        print(f"Auf Port {port} läuft kein Monitor für dieses Projekt.")
        pid_file.unlink(missing_ok=True)
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as ex:
        print(f"Monitor (PID {pid}) ließ sich nicht beenden: {ex}", file=sys.stderr)
        return 1
    pid_file.unlink(missing_ok=True)
    print(f"keel-Monitor auf Port {port} beendet.")
    return 0


def main():
    flags_with_value = {"--port", "--plugin-root", "--hours"}
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] not in flags_with_value]
    project = Path(args[0] if args else ".").resolve()
    if not (project / ".keel").is_dir():
        if "--if-autostart" in sys.argv:
            sys.exit(0)
        print(f"Kein keel-Projekt: {project}/.keel fehlt", file=sys.stderr)
        sys.exit(2)
    cfg = config_of(project)
    plugin_root = arg("--plugin-root") or os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parent.parent)
    port = int(arg("--port") or cfg.get("port") or DEFAULT_PORT)

    if "--stop" in sys.argv:
        sys.exit(stop(project))
    if "--ensure" in sys.argv:
        if "--if-autostart" in sys.argv and str(cfg.get("autostart", "")).lower() not in ("true", "ja", "yes", "1"):
            sys.exit(0)
        sys.exit(ensure(project, port, plugin_root, "--quiet" in sys.argv))

    Handler.project = project
    Handler.plugin_root = plugin_root
    Handler.hours = int(arg("--hours", "24"))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as ex:
        print(f"Port {port} belegt ({ex}). Läuft der Monitor schon? Sonst --port <N> oder monitor.port.", file=sys.stderr)
        sys.exit(1)
    print(f"keel-Monitor für {project.name}: http://127.0.0.1:{port}/  (Strg+C beendet)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
