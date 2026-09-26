#!/usr/bin/env python3
"""Flow monitor: a local web page that shows what keel is doing, with the handoffs as documentation.

Usage: monitor.py [project-dir] [--port N] [--plugin-root DIR] [--hours N]

Serves one page on http://127.0.0.1:<port>/ (default 8765) and a small JSON API:
  /api/state          situation report (lage.py), running role with its calling command, recent events
  /api/files          the Markdown files under .keel/ with their frontmatter, grouped by folder
  /api/file?path=...  one file under .keel/ (frontmatter and body)
  /api/doc?name=...   a document of the motor itself (docs/system.md, docs/konzept.md, agents, skills)

Observer only (System-ADR 0017): reads state, events and files, writes nothing, starts nothing.
Binds to 127.0.0.1 and answers only requests addressed to localhost.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent))
from frontmatter import parse as parse_fm  # noqa: E402
from lage import agent_runs, build_report, metrics_dir_of  # noqa: E402

PAGE = Path(__file__).parent / "monitor.html"
EVENT_TAIL = 200            # events.jsonl lines shown in the stream
HOOKS_TAIL_BYTES = 512_000  # tail of hooks.jsonl scanned for commands and skill calls
STATE_TTL = 2.0             # seconds a computed state is reused across polls and tabs


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


def state(project, plugin_root, hours):
    report, _ = build_report(project, hours, plugin_root)
    md = metrics_dir_of(project)
    events = parse_json_lines(tail_lines(md / "events.jsonl", 4_000_000))
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
    port = 8765
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


def main():
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[i - 1].startswith("--")]
    project = Path(args[0] if args else ".").resolve()
    if not (project / ".keel").is_dir():
        print(f"Kein keel-Projekt: {project}/.keel fehlt", file=sys.stderr)
        sys.exit(2)
    Handler.project = project
    Handler.plugin_root = arg("--plugin-root") or os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parent.parent)
    Handler.hours = int(arg("--hours", "24"))
    port = int(arg("--port", "8765"))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as ex:
        print(f"Port {port} belegt ({ex}). Läuft der Monitor schon? Sonst --port <N>.", file=sys.stderr)
        sys.exit(1)
    print(f"keel-Monitor für {project.name}: http://127.0.0.1:{port}/  (Strg+C beendet)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
