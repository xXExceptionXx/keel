#!/usr/bin/env python3
"""keel backlog port: one small contract, exchangeable adapters.

Usage (run from the project root or pass --project):
  backlog.py next                     highest-ranked item with status "bereit"
  backlog.py show <id>                one item
  backlog.py list [--status s]        items as JSON
  backlog.py propose <file.md>        new item with status "vorgeschlagen"; file has frontmatter titel, problem, warum, herkunft
  backlog.py status <id> <status>     status change within the canonical set
  backlog.py link <id> <plan-path>    link an item to its plan file

Canonical statuses: vorgeschlagen, bereit, in-arbeit, erledigt, verworfen.
Adapter is chosen by backlog.provider in .keel/config.yaml: markdown (default) or github.
Output is JSON on stdout; errors go to stderr with exit code 1.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import read as read_config  # noqa: E402
from frontmatter import parse as parse_fm  # noqa: E402

STATUSES = ["vorgeschlagen", "bereit", "in-arbeit", "erledigt", "verworfen"]
SECTION_TITLES = {"vorgeschlagen": "vorgeschlagen", "bereit": "bereit", "in-arbeit": "in Arbeit", "erledigt": "erledigt", "verworfen": "verworfen"}
FIELDS = ["problem", "warum", "herkunft", "plan"]


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- markdown adapter
class Markdown:
    def __init__(self, project, cfg):
        self.path = project / ".keel" / "backlog.md"

    def _load(self):
        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        items, status, item = [], None, None
        head = []
        for line in text.splitlines():
            m = re.match(r"^##\s+(.+?)\s*$", line)
            if m:
                title = m.group(1).strip().lower().replace(" ", "-")
                status = title if title in STATUSES else None
                item = None
                continue
            if status is None:
                head.append(line)
                continue
            m = re.match(r"^- \[([A-Za-z0-9-]+)\]\s+(.+?)\s*$", line)
            if m:
                item = {"id": m.group(1), "titel": m.group(2), "status": status, "rang": len([i for i in items if i["status"] == status]) + 1}
                items.append(item)
                continue
            m = re.match(r"^\s+([A-Za-z]+):\s*(.*)$", line)
            if m and item is not None:
                item[m.group(1).lower()] = m.group(2).strip()
        return items, head

    def _save(self, items, head):
        out = [l for l in head]
        while out and out[-1].strip() == "":
            out.pop()
        for st in STATUSES:
            out.append("")
            out.append(f"## {SECTION_TITLES[st]}")
            for it in [i for i in items if i["status"] == st]:
                out.append("")
                out.append(f"- [{it['id']}] {it['titel']}")
                for f in FIELDS:
                    if it.get(f):
                        out.append(f"  {f.capitalize()}: {it[f]}")
        self.path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")

    def list(self, status=None):
        items, _ = self._load()
        return [i for i in items if status is None or i["status"] == status]

    def show(self, id_):
        for i in self.list():
            if i["id"] == id_:
                return i
        fail(f"unknown backlog item {id_}")

    def propose(self, data):
        items, head = self._load()
        nums = [int(i["id"].split("-")[-1]) for i in items if re.match(r"^BL-\d+$", i["id"])]
        new = {"id": f"BL-{max(nums, default=0) + 1}", "titel": data["titel"], "status": "vorgeschlagen"}
        for f in FIELDS:
            if data.get(f):
                new[f] = data[f]
        items.append(new)
        self._save(items, head)
        return self.show(new["id"])

    def status(self, id_, status):
        items, head = self._load()
        for i in items:
            if i["id"] == id_:
                i["status"] = status
                self._save(items, head)
                return self.show(id_)
        fail(f"unknown backlog item {id_}")

    def link(self, id_, plan):
        items, head = self._load()
        for i in items:
            if i["id"] == id_:
                i["plan"] = plan
                self._save(items, head)
                return self.show(id_)
        fail(f"unknown backlog item {id_}")


# ---------------------------------------------------------------- github adapter
class GitHub:
    def __init__(self, project, cfg):
        gh = cfg.get("github", {}) if isinstance(cfg.get("github"), dict) else {}
        self.repo = gh.get("repo") or fail("backlog.github.repo missing in .keel/config.yaml")
        self.prefix = gh.get("label_prefix", "keel:")
        self.labels = {s: f"{self.prefix}{s}" for s in STATUSES}

    def _gh(self, *args, input_=None):
        r = subprocess.run(["gh", *args], capture_output=True, text=True, input=input_)
        if r.returncode != 0:
            fail(f"gh {' '.join(args[:2])} failed: {r.stderr.strip()}")
        return r.stdout

    def _parse(self, issue):
        item = {"id": f"#{issue['number']}", "titel": issue["title"], "status": "vorgeschlagen"}
        for l in issue.get("labels", []):
            name = l["name"]
            if name.startswith(self.prefix) and name[len(self.prefix):] in STATUSES:
                item["status"] = name[len(self.prefix):]
            m = re.match(r"^prio:(\d+)$", name)
            if m:
                item["prio"] = int(m.group(1))
        for line in (issue.get("body") or "").splitlines():
            m = re.match(r"^([A-Za-z]+):\s*(.*)$", line)
            if m and m.group(1).lower() in FIELDS:
                item[m.group(1).lower()] = m.group(2).strip()
        return item

    def list(self, status=None):
        out = self._gh("issue", "list", "-R", self.repo, "--state", "all", "--limit", "200", "--json", "number,title,labels,body,createdAt")
        items = [self._parse(i) for i in json.loads(out)]
        items = [i for i in items if status is None or i["status"] == status]
        items.sort(key=lambda i: (i.get("prio", 999), int(i["id"][1:])))
        for n, i in enumerate(items, 1):
            i["rang"] = n
        return items

    def show(self, id_):
        num = id_.lstrip("#")
        out = self._gh("issue", "view", num, "-R", self.repo, "--json", "number,title,labels,body")
        return self._parse(json.loads(out))

    def _ensure_labels(self):
        existing = json.loads(self._gh("label", "list", "-R", self.repo, "--json", "name", "--limit", "200"))
        names = {l["name"] for l in existing}
        for s, name in self.labels.items():
            if name not in names:
                self._gh("label", "create", name, "-R", self.repo, "--color", "0E8A16" if s == "bereit" else "C5DEF5", "--description", f"keel status {s}")

    def propose(self, data):
        self._ensure_labels()
        body = "\n".join(f"{f.capitalize()}: {data[f]}" for f in FIELDS if data.get(f))
        out = self._gh("issue", "create", "-R", self.repo, "--title", data["titel"], "--body", body, "--label", self.labels["vorgeschlagen"])
        num = out.strip().rsplit("/", 1)[-1]
        return self.show(f"#{num}")

    def status(self, id_, status):
        self._ensure_labels()
        num = id_.lstrip("#")
        current = self.show(id_)["status"]
        args = ["issue", "edit", num, "-R", self.repo, "--add-label", self.labels[status]]
        if current != status:
            args += ["--remove-label", self.labels[current]]
        self._gh(*args)
        if status in ("erledigt", "verworfen"):
            self._gh("issue", "close", num, "-R", self.repo, "--reason", "completed" if status == "erledigt" else "not planned")
        else:
            subprocess.run(["gh", "issue", "reopen", num, "-R", self.repo], capture_output=True, text=True)
        return self.show(id_)

    def link(self, id_, plan):
        num = id_.lstrip("#")
        item = self.show(id_)
        body = json.loads(self._gh("issue", "view", num, "-R", self.repo, "--json", "body"))["body"] or ""
        lines = [l for l in body.splitlines() if not re.match(r"^Plan:", l)]
        lines.append(f"Plan: {plan}")
        self._gh("issue", "edit", num, "-R", self.repo, "--body", "\n".join(lines))
        return self.show(id_)


ADAPTERS = {"markdown": Markdown, "github": GitHub}


def main(argv):
    project = Path.cwd()
    if "--project" in argv:
        i = argv.index("--project")
        project = Path(argv[i + 1]).resolve()
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        fail(__doc__)
    cfgfile = project / ".keel" / "config.yaml"
    cfg = read_config(cfgfile).get("backlog", {}) if cfgfile.exists() else {}
    if not isinstance(cfg, dict):
        cfg = {}
    # config.py flattens two levels only; read github.* keys manually
    gh = {}
    if cfgfile.exists():
        section = None
        for raw in cfgfile.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].rstrip()
            m = re.match(r"^(\s*)([A-Za-z0-9_.-]+):\s*(.*)$", line)
            if not m:
                continue
            indent, key, val = len(m.group(1)), m.group(2), m.group(3).strip().strip("\"'")
            if indent == 0:
                section = key
            elif indent == 2 and section == "backlog" and key == "github":
                section = "backlog.github"
            elif indent == 4 and section == "backlog.github" and val:
                gh[key] = val
    cfg["github"] = gh
    provider = cfg.get("provider", "markdown")
    adapter = ADAPTERS.get(provider) or fail(f"unknown backlog provider {provider}")
    a = adapter(project, cfg)

    cmd, args = argv[0], argv[1:]
    if cmd == "next":
        items = a.list("bereit")
        result = items[0] if items else None
    elif cmd == "show":
        result = a.show(args[0])
    elif cmd == "list":
        status = args[args.index("--status") + 1] if "--status" in args else None
        result = a.list(status)
    elif cmd == "propose":
        text = Path(args[0]).read_text(encoding="utf-8")
        data, body = parse_fm(text)
        if data is None:
            fail("propose file needs frontmatter with titel, problem, warum, herkunft")
        data = {k: (", ".join(v) if isinstance(v, list) else v) for k, v in data.items() if k != "__order__"}
        result = a.propose(data)
    elif cmd == "status":
        if args[1] not in STATUSES:
            fail(f"status must be one of {', '.join(STATUSES)}")
        result = a.status(args[0], args[1])
    elif cmd == "link":
        result = a.link(args[0], args[1])
    else:
        fail(__doc__)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
