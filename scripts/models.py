#!/usr/bin/env python3
"""Which model ran which role, and whether a model switch is waiting for the Coach.

Usage: models.py <project-dir> [--json]

Source: agent_stop events in the runtime folder of the project (keel path events), and the end of each briefing
(briefing_geprueft, briefing_protokoll_offen with model), which counts as a run of the Supervisor. Each carries `model` since
System-ADR 0015; older events fall back to the model in their subagent transcript while it exists.
A switch is per role: the model of the role's latest run differs from the model it mostly ran on before;
a single run on another model in between (fallback on overload) is not a switch.
It stays open until a Coach report names the new model under `modell_geprueft`.
Used by due.py (Fälligkeit) and metrics.py (Kennzahlen je Modell).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import _keel  # noqa: F401
from keel.store import events, frontmatter
from keel.store.paths import Paths


def transcript_model(path):
    """Model of the latest assistant turn in a transcript, or ''."""
    model = ""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400000))
            for line in f.read().decode("utf-8", "replace").splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") == "assistant":
                    m = (rec.get("message") or {}).get("model") or ""
                    if m and m != "<synthetic>":
                        model = m
    except OSError:
        pass
    return model


def load_events(project):
    """Events of the project with `_ts` in UTC; unusable lines are skipped (keel.store.events)."""
    return events.read(Paths(project).events).events


BRIEFING_ENDS = ("briefing_geprueft", "briefing_protokoll_offen")


def runs(events):
    """Role runs with a known model, oldest first: dicts with role, model, ts, agent_id, ref, result."""
    out = []
    for e in events:
        if e.get("event") in BRIEFING_ENDS and e.get("model"):
            # A briefing is the Supervisor in the main session; it counts as one of its runs (kern-befunde P2)
            out.append({"role": "supervisor", "model": e["model"], "ts": e["_ts"], "agent_id": e.get("session_id"),
                        "ref": "briefing", "result": "ok", "transcript": None})
            continue
        if e.get("event") != "agent_stop":
            continue
        model = e.get("model") or (transcript_model(e["transcript"]) if isinstance(e.get("transcript"), str) else "")
        if model:
            out.append({"role": e.get("role", "?"), "model": model, "ts": e["_ts"], "agent_id": e.get("agent_id"), "ref": e.get("ref") or "", "result": e.get("result"), "transcript": e.get("transcript")})
    return sorted(out, key=lambda r: r["ts"])


def checked_models(project):
    """Models a Coach report has already assessed (frontmatter `modell_geprueft`, scalar or list)."""
    seen = set()
    d = Path(project) / ".keel" / "work" / "coach"
    if not d.exists():
        return seen
    for p in d.glob("*.md"):
        v = frontmatter.fields_tolerant(p).get("modell_geprueft")
        if isinstance(v, list):
            seen.update(x for x in v if x)
        elif v:
            seen.add(v)
    return seen


def switches(project, role_runs=None):
    """Open model switches, one per new model: {modell, vorher, rollen, seit, laeufe}.

    `laeufe` counts runs on the new model since the switch, across all roles that now run on it.
    """
    role_runs = runs(load_events(project)) if role_runs is None else role_runs
    by_role = defaultdict(list)
    for r in role_runs:
        by_role[r["role"]].append(r)
    found = {}
    for role, rs in by_role.items():
        current = rs[-1]["model"]
        others = [i for i, r in enumerate(rs) if r["model"] != current]
        if not others:
            continue
        before = [r["model"] for r in rs[: others[-1] + 1]]
        previous = max((m for m in set(before) if m != current), key=before.count)
        if before.count(current) >= before.count(previous):
            continue  # the current model was already established; the other one was a fallback blip
        last_prev = max(i for i, r in enumerate(rs) if r["model"] == previous)
        first = next(r for r in rs[last_prev + 1 :] if r["model"] == current)
        s = found.setdefault(current, {"modell": current, "vorher": set(), "rollen": set(), "seit": first["ts"]})
        s["vorher"].add(previous)
        s["rollen"].add(role)
        s["seit"] = min(s["seit"], first["ts"])
    done = checked_models(project)
    out = []
    for m, s in found.items():
        if m in done:
            continue
        # every role now on the new model counts, also one without history (e.g. first reviewer runs)
        now_on = {role for role, rs in by_role.items() if rs[-1]["model"] == m}
        n = sum(1 for r in role_runs if r["model"] == m and r["role"] in now_on and r["ts"] >= s["seit"])
        out.append({"modell": m, "vorher": sorted(s["vorher"]), "rollen": sorted(s["rollen"]), "seit": s["seit"].date().isoformat(), "laeufe": n})
    return sorted(out, key=lambda s: s["seit"])


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    project = Path(sys.argv[1]).resolve()
    rr = runs(load_events(project))
    latest = {}
    for r in rr:
        latest[r["role"]] = r["model"]
    result = {"aktuell_je_rolle": latest, "offene_wechsel": switches(project, rr)}
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for role, m in sorted(latest.items()):
        print(f"{role}: {m}")
    for s in result["offene_wechsel"]:
        print(f"Wechsel: {s['modell']} seit {s['seit']} (vorher {', '.join(s['vorher'])}; Rollen {', '.join(s['rollen'])}; {s['laeufe']} Läufe)")


if __name__ == "__main__":
    main()
