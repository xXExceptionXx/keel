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
Output is JSON on stdout; errors go to stderr with exit code 1, usage errors with exit code 2.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import _keel  # noqa: F401
from keel.domain.errors import KeelError
from keel.store import config, frontmatter
from keel.store.io import atomic_write, file_lock

STATUSES = ["vorgeschlagen", "bereit", "in-arbeit", "erledigt", "verworfen"]
SECTION_TITLES = {"vorgeschlagen": "vorgeschlagen", "bereit": "bereit", "in-arbeit": "in Arbeit", "erledigt": "erledigt", "verworfen": "verworfen"}
FIELDS = ["problem", "warum", "herkunft", "plan"]


def fail(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- markdown adapter
HEADING = re.compile(r"^##\s+(.+?)\s*$")
ITEM = re.compile(r"^- \[([A-Za-z0-9-]+)\]\s+(.+?)\s*$")
FIELD = re.compile(r"^\s+([A-Za-z]+):\s*(.*)$")


class Markdown:
    """.keel/backlog.md. A change rewrites only the lines of the affected item (F5): unknown fields, multi-line
    values, prose and headings stay byte for byte, line endings (LF or CRLF) included. An item is its line
    "- [ID] Titel" plus the following indented lines, also across blank lines; the first line that is not indented
    (prose, another item, a heading) ends it. Changes run under a lock and are written atomically (N6)."""

    def __init__(self, project, cfg):
        self.path = project / ".keel" / "backlog.md"
        self.newline = "\n"

    def _lines(self):
        if not self.path.exists():
            return self._empty()
        text = self.path.read_bytes().decode("utf-8")
        self.newline = "\r\n" if "\r\n" in text else "\n"
        return text.replace("\r\n", "\n").split("\n")

    @staticmethod
    def _empty():
        out = ["# Backlog"]
        for st in STATUSES:
            out += ["", f"## {SECTION_TITLES[st]}"]
        return out + [""]

    @staticmethod
    def _status_of(heading):
        title = heading.strip().lower().replace(" ", "-")
        return title if title in STATUSES else None

    def _parse(self, lines):
        """Items with their line range [start, end) and the line range of each known section."""
        items, sections = [], {}
        status, current = None, None
        for i, line in enumerate(lines):
            m = HEADING.match(line)
            if m:
                status = self._status_of(m.group(1))
                if status:
                    sections.setdefault(status, [i, len(lines)])
                for st, rng in sections.items():
                    if rng[0] < i and rng[1] == len(lines):
                        rng[1] = i
                current = None
                continue
            if line.startswith("#"):
                current = None
                continue
            if status is None:
                continue
            m = ITEM.match(line)
            if m:
                rank = len([x for x in items if x["status"] == status]) + 1
                current = {"id": m.group(1), "titel": m.group(2), "status": status, "rang": rank, "_start": i, "_end": i + 1}
                items.append(current)
                continue
            if current is not None and not line.strip():
                continue  # a blank line ends the item only if no indented line follows
            if current is not None and line[:1] in (" ", "\t"):
                current["_end"] = i + 1
                m = FIELD.match(line)
                if m and m.group(1).lower() not in current:
                    current[m.group(1).lower()] = m.group(2).strip()
                continue
            current = None
        return items, sections

    @staticmethod
    def _public(item):
        return {k: v for k, v in item.items() if not k.startswith("_")}

    def _save(self, lines):
        atomic_write(self.path, self.newline.join(lines))

    def _find(self, items, id_):
        for i in items:
            if i["id"] == id_:
                return i
        fail(f"unknown backlog item {id_}")

    def _insert(self, lines, sections, status, block):
        """Insert block (with a blank line before it) at the end of the section's items."""
        if status not in sections:
            while lines and lines[-1] == "":
                lines.pop()
            lines += ["", f"## {SECTION_TITLES[status]}", "", *block, ""]
            return
        start, end = sections[status]
        at = end
        while at - 1 > start and lines[at - 1].strip() == "":
            at -= 1
        lines[at:at] = ["", *block]

    def list(self, status=None):
        items, _ = self._parse(self._lines())
        return [self._public(i) for i in items if status is None or i["status"] == status]

    def show(self, id_):
        items, _ = self._parse(self._lines())
        return self._public(self._find(items, id_))

    def propose(self, data):
        with file_lock(self.path):
            lines = self._lines()
            items, sections = self._parse(lines)
            # every BL id in the file counts, also one under a heading that is not a status
            nums = [int(n) for n in re.findall(r"^- \[BL-(\d+)\]", "\n".join(lines), flags=re.M)]
            new_id = f"BL-{max(nums, default=0) + 1}"
            block = [f"- [{new_id}] {one_line(data['titel'])}"]
            block += [f"  {f.capitalize()}: {one_line(data[f])}" for f in FIELDS if data.get(f)]
            self._insert(lines, sections, "vorgeschlagen", block)
            self._save(lines)
        return self.show(new_id)

    def status(self, id_, status):
        with file_lock(self.path):
            lines = self._lines()
            items, _ = self._parse(lines)
            item = self._find(items, id_)
            if item["status"] != status:
                block = lines[item["_start"]:item["_end"]]
                start = item["_start"] - 1 if item["_start"] > 0 and lines[item["_start"] - 1] == "" else item["_start"]
                del lines[start:item["_end"]]
                _, sections = self._parse(lines)
                self._insert(lines, sections, status, block)
                self._save(lines)
        return self.show(id_)

    def link(self, id_, plan):
        with file_lock(self.path):
            lines = self._lines()
            item = self._find(self._parse(lines)[0], id_)
            row = f"  Plan: {one_line(plan)}"
            for i in range(item["_start"] + 1, item["_end"]):
                if re.match(r"^\s+Plan:", lines[i]):
                    lines[i] = row
                    break
            else:
                lines.insert(item["_end"], row)
            self._save(lines)
        return self.show(id_)


def one_line(value):
    return " ".join(str(value).split())


# ---------------------------------------------------------------- github adapter
class GitHub:
    def __init__(self, project, cfg):
        gh = cfg.get("github", {}) if isinstance(cfg.get("github"), dict) else {}
        self.repo = gh.get("repo") or fail("backlog.github.repo missing in .keel/config.yaml")
        self.prefix = gh.get("label_prefix") or "keel:"
        named = gh.get("labels") if isinstance(gh.get("labels"), dict) else {}
        self.labels = {s: named.get(s.replace("-", "_")) or f"{self.prefix}{s}" for s in STATUSES}
        self.status_of_label = {v: k for k, v in self.labels.items()}

    def _gh(self, *args, input_=None):
        r = subprocess.run(["gh", *args], capture_output=True, text=True, input=input_)
        if r.returncode != 0:
            fail(f"gh {' '.join(args[:2])} failed: {r.stderr.strip()}")
        return r.stdout

    def _parse(self, issue):
        item = {"id": f"#{issue['number']}", "titel": issue["title"], "status": "vorgeschlagen"}
        for l in issue.get("labels", []):
            name = l["name"]
            if name in self.status_of_label:
                item["status"] = self.status_of_label[name]
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


USAGE_ARGS = {"show": 1, "propose": 1, "status": 2, "link": 2}


def main(argv):
    project = Path.cwd()
    if "--project" in argv:
        i = argv.index("--project")
        if i + 1 >= len(argv):
            fail(__doc__, 2)
        project = Path(argv[i + 1]).resolve()
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        fail(__doc__, 2)
    cmd, args = argv[0], argv[1:]
    if cmd not in ("next", "list", *USAGE_ARGS) or len(args) < USAGE_ARGS.get(cmd, 0):
        fail(__doc__, 2)
    try:
        cfg = config.section(config.load(project), "backlog")
    except KeelError as exc:
        fail(f"backlog: {exc}", 2)
    provider = cfg.get("provider") or "markdown"
    adapter = ADAPTERS.get(provider) or fail(f"unknown backlog provider {provider}")
    a = adapter(project, cfg)

    if cmd == "next":
        items = a.list("bereit")
        result = items[0] if items else None
    elif cmd == "show":
        result = a.show(args[0])
    elif cmd == "list":
        status = args[args.index("--status") + 1] if "--status" in args[:-1] else None
        result = a.list(status)
    elif cmd == "propose":
        try:
            data, _ = frontmatter.load(args[0])
        except KeelError as exc:
            fail(f"backlog: {exc}", 2)
        if data is None:
            fail("propose file needs frontmatter with titel, problem, warum, herkunft")
        data = {k: (", ".join(v) if isinstance(v, list) else v) for k, v in data.items() if k != "__order__"}
        if not data.get("titel"):
            fail("propose file needs a titel")
        result = a.propose(data)
    elif cmd == "status":
        if args[1] not in STATUSES:
            fail(f"status must be one of {', '.join(STATUSES)}")
        result = a.status(args[0], args[1])
    else:
        result = a.link(args[0], args[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
