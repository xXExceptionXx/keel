"""SubagentStop (gate): a role's handoff is only complete when its output file has the right status and the
closing message has at most three lines; otherwise the stop is blocked and the role keeps working. Runs the
Prüftor, the diff limit and the compliance scan for the developer, checks the ADR level of every role
(System-ADR 0021) and forces budget-erschoepft when the tool-call budget is used up.

Each role's exit rules are a function below, carried over unchanged from hooks/agent-stop.sh; M3 turns them into
tables in keel.domain."""
import glob
import json
import re
import subprocess
import time
from pathlib import Path

from keel.services import adr
from keel.services.hooks import files, legacy
from keel.services.hooks.base import CannotCheck, keel_role
from keel.store import frontmatter, transcripts


class _Stop(Exception):
    """Ends the checks: the stop is blocked (result is a Refuse) or allowed (result None)."""

    def __init__(self, result):
        self.result = result


def run(hook):
    role = keel_role(hook.text("agent_type"))
    if not role:
        return None
    hook.role = role
    hook.agent_id = hook.text("agent_id")
    stop = _AgentStop(hook)
    try:
        stop.check()
    except _Stop as done:
        return done.result
    return stop.finish("ok")


class _AgentStop:
    def __init__(self, hook):
        self.hook = hook
        self.role = hook.role
        self.id = hook.agent_id
        self.proj = hook.project
        self.rt = hook.runtime
        state = self.rt.agent(self.id)
        self.ref = state["ref"]
        hook.ref = self.ref
        self.calls = state["calls"] if state["calls"] is not None else 0
        self.tasks = self.proj / ".keel" / "work" / "tasks"
        self.plans = self.proj / ".keel" / "work" / "plans"
        msg = hook.text("last_assistant_message")
        self.lines = sum(1 for line in msg.split("\n") if line.strip())

    # -- results ----------------------------------------------------------------------------------------------

    def block(self, reason):
        raise _Stop(self.hook.block_stop(reason))

    def finish(self, result):
        """Record the run, drop its state, allow the stop. The model is what actually ran, for the Coach."""
        tr = self.hook.text("agent_transcript_path")
        self.hook.try_record("agent_stop", {"role": self.role, "agent_id": self.id, "ref": self.ref,
                                            "calls": self.calls, "lines": self.lines, "result": result,
                                            "transcript": tr, "model": transcripts.last_model(tr)})
        self.rt.finish_agent(self.id, self.role)
        return None

    def done(self, result="ok"):
        raise _Stop(self.finish(result))

    def require(self, problem, message):
        """Block with message (which may use {p}, the problem) when the check found a problem."""
        if problem:
            self.block(message.format(p=problem))

    # -- the checks -------------------------------------------------------------------------------------------

    def check(self):
        limit = self.hook.role_limit(self.role, "tool_calls", 60)
        if not limit.isdigit():
            raise CannotCheck(f"Werkzeugbudget für {self.role} in .keel/config.yaml ist keine ganze Zahl: '{limit}'")

        # ADRs only on the role's own level (System-ADR 0021). Before the budget shortcut: an exhausted budget must
        # not carry an ADR on a foreign level past this check; tool-gate lets the role still edit .keel/adr/.
        if self.role != "probe":
            try:
                before = self.rt.adr_snapshot(self.id, self.role)
            except Exception as exc:  # noqa: BLE001
                raise CannotCheck(f"ADR-Stufe nicht prüfbar: {exc}") from exc
            if before is None:
                raise CannotCheck(f"ADR-Stand vom Rollenstart fehlt (Agent {self.id})")
            try:
                problems = adr.compare(self.proj, before, self.role)
            except Exception as exc:  # noqa: BLE001 - any failure here means the level cannot be checked
                raise CannotCheck(f"ADR-Stufe nicht prüfbar: {exc}") from exc
            if problems:
                self.block("ADR auf fremder Stufe: " + " ".join(problems))

        # Tool-call budget exhausted: force the state, allow the stop so the loop ends deterministically.
        task = self.tasks / f"{self.ref}.md"
        if self.calls > int(limit) and self.ref and task.is_file():
            self.set(task, status="budget-erschoepft")
            self.done("budget-erschoepft")

        if self.lines > 3:
            self.block(f"Abschlussnachricht hat {self.lines} Zeilen, erlaubt sind drei. Details gehören in die "
                       "Übergabe-Datei, nicht in die Nachricht.")

        getattr(self, f"role_{self.role}", self.role_unknown)()

    def set(self, path, **values):
        try:
            data, _ = frontmatter.load(path)
            if data is None:
                raise CannotCheck(f"{path}: no frontmatter found")
            frontmatter.update(path, values)
        except CannotCheck:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CannotCheck(f"{path} nicht schreibbar: {exc}") from exc

    def role_unknown(self):
        pass

    def role_probe(self):
        self.done()

    def role_planer(self):
        task = self.tasks / f"{self.ref}.md"
        if task.is_file():
            # Neuschnitt: the task is re-cut in place, replaced or discarded
            self.require(files.check(task, typ="aufgabe", status="geplant,ersetzt,verworfen"),
                         "Neuschnitt unvollständig: {p}. Erlaubt: geplant (neu geschnitten, tests: []), ersetzt (neue "
                         "Aufgaben im Plan) oder verworfen.")
            if files.get(task, "status") == "geplant" and files.get(task, "tests"):
                self.block("Neu geschnittene Aufgabe muss tests: [] haben, der Tester schreibt sie neu.")
            vh = files.get(task, "vorhaben")
            if not vh:
                self.block(f"Aufgabe {self.ref} hat kein Feld 'vorhaben'; ohne es lässt sich die Aufgabenliste des "
                           "Plans nicht prüfen.")
            planfile = files.find(self.plans, vorhaben=vh)
            if not planfile:
                self.block(f"Kein Plan mit 'vorhaben: {vh}' unter .keel/work/plans/; prüfe das Feld 'vorhaben' der "
                           f"Aufgabe {self.ref}.")
            for t in files.items(files.get(planfile, "aufgaben")):
                self.require(files.check(self.tasks / f"{t}.md", typ="aufgabe",
                                         status="geplant,tests-bereit,in-arbeit,fertig,review,nacharbeit",
                                         require=("id", "vorhaben", "titel")),
                             "Plan-Aufgabenliste verweist auf unbrauchbare Aufgabe: {p}. Ersetzte und verworfene "
                             "Aufgaben gehören nicht in 'aufgaben'.")
        else:
            plan = self.plans / f"{self.ref}.md"
            self.require(files.check(plan, typ="plan", status="geplant", nonempty=("aufgaben",)),
                         "Übergabe unvollständig: {p}. Setze status: geplant und trage die Aufgaben-IDs in "
                         "'aufgaben' ein.")
            for t in files.items(files.get(plan, "aufgaben")):
                self.require(files.check(self.tasks / f"{t}.md", typ="aufgabe", status="geplant",
                                         require=("id", "vorhaben", "titel"), nonempty=("dateien", "referenz")),
                             "Aufgaben-Datei fehlt oder unvollständig: {p}")

    def role_po(self):
        if self.ref.startswith("epic:"):
            self._po_epic(self.ref[len("epic:"):])
        planfile = self.plans / f"{self.ref}.md"
        if not planfile.is_file():
            self.block(f"Plan-Datei {planfile} fehlt")
        st = files.get(planfile, "status")
        if not st:
            self.block(f"Plan {self.ref} hat keinen Status; setze status im Frontmatter.")
        if st == "entwurf":
            self.require(files.check(planfile, typ="plan", require=("vorhaben", "titel", "backlog", "abstimmung")),
                         "Plan unvollständig: {p}")
            for sec in ("## Problemstellung", "## Pflichtkriterien", "## Akzeptanzkriterien"):
                if not files.has_line(planfile, sec):
                    self.block(f"Plan-Abschnitt fehlt: {sec}")
        elif st == "problemstellung":
            if files.get(planfile, "abstimmung") != "einig":
                self.block("status problemstellung verlangt abstimmung: einig")
        elif st == "blockiert":
            if files.get(planfile, "abstimmung") != "vorlage":
                self.block("status blockiert verlangt abstimmung: vorlage")
        elif st == "abgenommen":
            if files.check(planfile, nonempty=("abgenommen", "abgenommen_von")):
                self.block("Abnahme braucht abgenommen=<Datum> und abgenommen_von=PO")
        elif st == "nacharbeit":
            if not files.has_line(planfile, "## Nacharbeit"):
                self.block("status nacharbeit verlangt einen Abschnitt '## Nacharbeit'")
        elif st == "abnahme-bereit":
            self.block("Abnahme nicht entschieden: setze status=abgenommen oder status=nacharbeit")
        # Klärung: any task of this plan with a pending clarification must be answered
        for t in sorted(self.tasks.glob("*.md")) if self.tasks.is_dir() else []:
            if not files.has_line(t, "## Klärung"):
                continue
            if files.get(t, "status") == "neuschnitt":
                k, t_vh, p_vh = files.get(t, "klaerung"), files.get(t, "vorhaben"), files.get(planfile, "vorhaben")
                if not (k in ("beantwortet", "vorlage") or t_vh != p_vh):
                    self.block(f"Klärung in {t.name} nicht beantwortet: setze klaerung=beantwortet mit '## Antwort "
                               "des PO' oder klaerung=vorlage")

    def _po_epic(self, name):
        ep = self.proj / ".keel" / "work" / "epics" / f"{name}.md"
        self.require(files.check(ep, typ="epic", status="skizze,bewertet,leitentscheidungen-offen,aktiv,fertig",
                                 require=("epic", "titel", "backlog")),
                     "Epic-Datei fehlt oder unvollständig: {p}")
        st = files.get(ep, "status")
        if st == "skizze":
            for sec in ("## Zielbild des Themas", "## Vorhaben", "## Leitfragen", "## Done-Condition"):
                if not files.has_line(ep, sec):
                    self.block(f"Epic-Abschnitt fehlt: {sec}")
            if not files.get(ep, "vorhaben"):
                self.block("Epic: Frontmatter 'vorhaben' ist leer; trage die Plan-Namen der Vorhaben in Reihenfolge ein")
        elif st == "bewertet":
            self.block("Epic-Abstimmung nicht abgeschlossen: setze status=aktiv (alle Leitentscheidungen als ADR) oder "
                       "status=leitentscheidungen-offen (Vorlagen geschrieben)")
        elif st == "leitentscheidungen-offen":
            if not glob.glob(str(self.proj / ".keel" / "decisions" / "pending") + f"/*epic-{glob.escape(name)}*"):
                self.block(f"status leitentscheidungen-offen ohne Vorlage unter .keel/decisions/pending/*epic-{name}*")
        elif st == "aktiv":
            if not files.get(ep, "leitentscheidungen"):
                self.block("status aktiv verlangt Leitentscheidungen als ADR-Nummern im Frontmatter")
            if not files.has_line(ep, "## Leitentscheidungen"):
                self.block("Abschnitt '## Leitentscheidungen' fehlt")
        elif st == "fertig":
            if files.check(ep, nonempty=("abgenommen", "abgenommen_von")):
                self.block("Epic-Abnahme braucht abgenommen=<Datum> und abgenommen_von=PO")
        self.done()

    def role_architekt(self):
        if self.ref.startswith("epic:"):
            ep = self.proj / ".keel" / "work" / "epics" / f"{self.ref[len('epic:'):]}.md"
            if not ep.is_file():
                self.block(f"Epic-Datei {ep} fehlt")
            st = files.get(ep, "status")
            if st == "bewertet":
                if not files.has_line(ep, "## Epic-Bewertung des Architekten"):
                    self.block("Abschnitt '## Epic-Bewertung des Architekten' (Kurzfassung) fehlt in der Epic-Datei")
                anl = Path(str(ep)[:-len(".md")] + ".bewertung.md")
                self.require(files.check(anl, typ="epic-bewertung", require=("epic", "datum")),
                             "Anlage fehlt oder unvollständig: {p}")
                if not files.contains(anl, "Tragende Entscheidungen"):
                    self.block("Anlage ohne 'Tragende Entscheidungen'")
            elif st in ("aktiv", "kurskorrektur"):
                if not files.has_line(ep, "## Retrospektiven"):
                    self.block("Abschnitt '## Retrospektiven' fehlt")
                if st == "kurskorrektur" and not files.contains(ep, "kurskorrektur:", ignore_case=True):
                    self.block("status kurskorrektur ohne Eintrag 'kurskorrektur: …' in den Retrospektiven")
            else:
                self.block(f"Epic-Status '{st}' nach Architekt unerwartet; erlaubt: bewertet (Epic-Bewertung) oder "
                           "aktiv|kurskorrektur (Retrospektive)")
            self.done()
        if self.ref.startswith(("bestandsaufnahme:", "wochenrunde:")):
            modus, datum = self.ref.split(":", 1)
            folder = self.proj / ".keel" / "work" / "architektur"
            rep = folder / (f"bestand-{datum}.md" if modus == "bestandsaufnahme" else f"woche-{datum}.md")
            self.require(files.check(rep, typ="architekturbericht", status="passt,abweichungen",
                                     require=("datum", "modus")),
                         f"Architekturbericht fehlt oder unvollständig ({rep}): {{p}}")
            if modus == "bestandsaufnahme" and not files.contains(self.proj / ".keel" / "architektur.md",
                                                                   "Referenzbeispiel"):
                self.block("architektur.md ohne Referenzbeispiele")
            if modus == "wochenrunde":
                max_pflege = self.hook.cfg_int("pflege.max_aufgaben_pro_runde", 2)
                n = files.count_lines(rep, r"^- .+ – .+ – wird Pflege")
                if n > max_pflege:
                    self.block(f"Wochenrunde schlägt {n} Pflegeaufgaben vor, erlaubt sind {max_pflege}. Bündeln oder "
                               "den Rest offen lassen.")
            return
        planfile = self.plans / f"{self.ref}.md"
        if not planfile.is_file():
            self.block(f"Plan-Datei {planfile} fehlt")
        if files.get(planfile, "status") == "entwurf":
            if files.check(planfile, nonempty=("bewertung", "abstimmung_runde")):
                self.block("Bewertung fehlt: setze bewertung=passt|anpassung|struktur und abstimmung_runde")
            if not files.has_line(planfile, "## Bewertung des Architekten"):
                self.block("Abschnitt '## Bewertung des Architekten (Runde n)' fehlt")
        else:
            self.require(files.check(planfile, typ="plan", status="abnahmetests-bereit,blockiert"),
                         "Strukturfrage: {p}. Erlaubt: abnahmetests-bereit (Antwort) oder blockiert (ADR-Entwurf).")
            if not files.has_line(planfile, "## Antwort des Architekten"):
                self.block("Abschnitt '## Antwort des Architekten' fehlt")

    def role_supervisor(self):
        vname = Path(self.ref).name
        decisions = self.proj / ".keel" / "decisions"
        done_f, pend_f = decisions / "done" / vname, decisions / "pending" / vname
        if done_f.is_file():
            self.require(files.check(done_f, typ="vorlage", status="entschieden", nonempty=("entscheidung", "entschieden")),
                         "Entschiedene Vorlage unvollständig: {p}")
            if files.get(done_f, "entscheider") != "Supervisor":
                self.block("Setze entscheider=Supervisor in der Vorlage")
            if files.get(done_f, "vorgelegt") != "offen":
                self.block("Setze vorgelegt=offen, damit das Briefing die Entscheidung zeigt")
            if not files.contains(done_f, "Warum nicht der Mensch"):
                self.block("Abschnitt '## Entscheidung des Supervisors' mit 'Warum nicht der Mensch:' fehlt")
            if not files.find(self.proj / ".keel" / "adr", vorlage=vname):
                self.block(f"Kein ADR mit 'vorlage: {vname}' unter .keel/adr/ gefunden")
        elif pend_f.is_file():
            if files.get(pend_f, "eskaliert") != "Supervisor":
                self.block("Vorlage weder entschieden (nach done/ verschoben) noch eskaliert (eskaliert=Supervisor, "
                           "richtungsweisend=<Grund>)")
            if files.check(pend_f, nonempty=("richtungsweisend", "eskaliert_am")):
                self.block("Eskalation braucht richtungsweisend=<Grund> und eskaliert_am=<Datum>")
        else:
            self.block(f"Vorlage {vname} weder unter pending/ noch unter done/")

    def role_compliance(self):
        rep = self.proj / ".keel" / "work" / "compliance" / f"{self.ref}.md"
        self.require(files.check(rep, typ="compliance", status="frei,auflagen,vorlage", require=("aufgabe", "datum")),
                     f"Compliance-Datei fehlt oder unvollständig ({rep}): {{p}}")
        task = self.tasks / f"{self.ref}.md"
        if not task.is_file():
            self.block(f"Aufgabe {self.ref} fehlt")
        t_comp, r_st = files.get(task, "compliance"), files.get(rep, "status")
        if not (r_st and t_comp == r_st):
            self.block("Setze compliance=<ergebnis> in der Aufgaben-Datei, gleich dem Status der Compliance-Datei")

    def role_coach(self):
        rep = self.proj / ".keel" / "work" / "coach" / f"{self.ref}.md"
        self.require(files.check(rep, typ="coachbericht", require=("datum", "kennzahlen_verletzt", "vorschlaege")),
                     f"Coach-Bericht fehlt oder unvollständig ({rep}): {{p}}")
        # Every Vorlage of the Coach says whether it concerns the project or the motor (System-ADR 0021).
        try:
            mine = files.find_all(self.proj / ".keel" / "decisions" / "pending", von="Coach")
        except Exception as exc:  # noqa: BLE001
            raise CannotCheck(f"Vorlagen nicht lesbar: {exc}") from exc
        for v in mine:
            if files.get(v, "ebene") not in ("projekt", "motor"):
                rel = Path(v).relative_to(self.proj) if Path(v).is_relative_to(self.proj) else v
                self.block(f"Vorlage {rel} ohne gültige ebene: setze ebene=projekt (alles unter .keel/) oder "
                           "ebene=motor (Hooks, Skripte, Skills, Rollen, Standardwerte des Plugins); betrifft sie "
                           "beides, teile sie.")
        # A model switch with enough runs for a comparison must be assessed (System-ADR 0015).
        need = self.hook.cfg("faelligkeiten.coach_nach_modellwechsel_rollenlaeufe", "10")
        need = int(need) if need.isdigit() else 10
        rc, out, err = legacy.run("models.py", self.proj, "--json")
        if rc != 0:
            raise CannotCheck(f"Modellwechsel nicht prüfbar, models.py endete mit {rc}: "
                              + "\n".join(err.splitlines()[:3]))
        try:
            open_sw = ", ".join(w["modell"] for w in json.loads(out)["offene_wechsel"] if w["laeufe"] >= need)
        except (ValueError, KeyError, TypeError) as exc:
            raise CannotCheck(f"Modellwechsel nicht prüfbar, models.py lieferte keine lesbare Antwort: {exc}") from exc
        if open_sw:
            self.block(f"Modellwechsel nicht bewertet: {open_sw}. Vergleiche je Rolle altes und neues Modell "
                       "(metrics.py, Tabelle 'Je Modell'), schreibe den Abschnitt '**Modellzuordnung:**' und setze "
                       f"modell_geprueft=[{open_sw}] im Bericht.")
        if files.get(rep, "modell_geprueft") and not files.contains(rep, "Modellzuordnung"):
            self.block("modell_geprueft ist gesetzt, aber der Abschnitt '**Modellzuordnung:**' fehlt im Bericht.")

    def role_auditor(self):
        audit = self.proj / ".keel" / "work" / "audit"
        rep = audit / f"{self.ref}.md"
        if (audit / f"woche-{self.ref}.md").is_file() and not rep.is_file():
            rep = audit / f"woche-{self.ref}.md"
        self.require(files.check(rep, typ="pruefbericht", status="passt,abweichungen", require=("datum", "modus", "seit")),
                     f"Prüfbericht fehlt oder unvollständig ({rep}): {{p}}. Pflichtfelder: typ pruefbericht, datum, "
                     "modus, seit, status passt|abweichungen.")

    def role_tester(self):
        task = self.tasks / f"{self.ref}.md"
        if task.is_file():
            self.require(files.check(task, typ="aufgabe", status="tests-bereit", nonempty=("tests",)),
                         "Übergabe unvollständig: {p}. Setze status: tests-bereit und liste die Testdateien in 'tests'.")
        else:
            self.require(files.check(self.plans / f"{self.ref}.md", typ="plan", status="abnahmetests-bereit",
                                     nonempty=("abnahmetests",)),
                         "Übergabe unvollständig: {p}. Setze status: abnahmetests-bereit und liste die Testdateien in "
                         "'abnahmetests'.")

    def role_entwickler(self):
        task = self.tasks / f"{self.ref}.md"
        self.require(files.check(task, typ="aufgabe", status="fertig-gemeldet,testeinspruch"),
                     "Übergabe unvollständig: {p}. Erlaubt: fertig-gemeldet (mit nachweis) oder testeinspruch (mit "
                     "begruendung).")
        if files.get(task, "status") != "fertig-gemeldet":
            if files.check(task, nonempty=("begruendung",)):
                self.block("Testeinspruch braucht das Feld 'begruendung'.")
            return
        if files.check(task, nonempty=("nachweis",)):
            self.block("Feld 'nachweis' fehlt: trage die Testausgabe in Kurzform ein.")
        with self.rt.activity("prueftor", self.ref):
            rc, out, _ = legacy.run("gate.sh", self.proj, self.ref, merge=True)
        if rc != 0:
            self.block(f"Prüftor rot. {legacy.strip(out)}")
        self._diff_limit(task)
        with self.rt.activity("compliance-scan", self.ref):
            rc, scan, _ = legacy.run("compliance_scan.py", self.proj, merge=True)
        scan = legacy.strip(scan)
        if rc not in (0, 3, 4, 5):
            tail = "".join(line + " " for line in scan.splitlines()[-3:])
            self.block(f"Compliance-Scan fehlgeschlagen (Code {rc}), die Aufgabe ist ungeprüft: {tail}/keel:hilfe "
                       "erklärt den Stand.")
        folder = self.proj / ".keel" / "work" / "compliance"
        folder.mkdir(parents=True, exist_ok=True)
        first = scan.splitlines()[0] if scan else ""
        m = re.match(r"^compliance: ([a-z]+)", first)
        ergebnis = m.group(1) if m else first
        (folder / f"{self.ref}.scan.md").write_text(
            f"---\ntyp: compliance-scan\naufgabe: {self.ref}\ndatum: {time.strftime('%Y-%m-%d')}\n"
            f"ergebnis: {ergebnis}\n---\n\n```\n{scan}\n```\n", encoding="utf-8")
        if rc == 5:
            hits = "".join(line + " " for line in [x for x in scan.splitlines() if "[block]" in x][:3])
            self.block("Compliance blockiert: Secret, Stub (TODO, not implemented) oder übersprungener Test im Diff. "
                       "Eine Aufgabe ist fertig oder nicht; Platzhalter gehören als Testeinspruch oder Stand in die "
                       f"Aufgaben-Datei. {hits}")
        self.set(task, compliance={4: "vorlage", 3: "pruefen", 0: "frei"}[rc])

    def _diff_limit(self, task):
        excl = [":(exclude).keel"] + [f":(exclude){t}" for t in files.items(files.get(task, "tests"))]
        head = subprocess.run(["git", "-C", str(self.proj), "rev-parse", "-q", "--verify", "HEAD"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if head.returncode != 0:
            self.block("Repository ohne Commit: der Diff der Aufgabe lässt sich nicht messen. Lege einen ersten "
                       "Commit an.")
        diff = subprocess.run(["git", "diff", "--numstat", "HEAD", "--", ".", *excl], cwd=str(self.proj),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if diff.returncode != 0:
            raise CannotCheck(f"git diff endete mit {diff.returncode}: {diff.stderr.decode('utf-8', 'replace').strip()}")
        lines = 0
        for row in diff.stdout.decode("utf-8", "replace").splitlines():
            parts = row.split("\t")
            lines += sum(int(x) for x in parts[:2] if x.isdigit())
        max_diff = self.hook.cfg_int("budget.diff_lines", 300)
        if lines > max_diff:
            self.block(f"Diff hat {lines} Zeilen, erlaubt sind {max_diff}. Setze status: budget-erschoepft und "
                       "beschreibe den Stand, der Planer schneidet neu.")

    def role_reviewer(self):
        task = self.tasks / f"{self.ref}.md"
        runde = files.get(task, "review_runde")
        if not runde:
            self.block(f"Aufgabe {self.ref} hat kein Feld 'review_runde'; ohne es ist die Review-Datei nicht zuzuordnen.")
        rev = self.proj / ".keel" / "work" / "reviews" / f"{self.ref}-r{runde}.md"
        self.require(files.check(rev, typ="review", status="bestanden,befunde", require=("aufgabe", "runde")),
                     f"Review-Datei fehlt oder unvollständig ({rev}): {{p}}")
        # Threshold and trend are computed, not judged; the Lead reads review_ergebnis (System-ADR 0018)
        rc, _, err = legacy.run("review.py", "pruefen", self.proj, self.ref)
        if rc != 0:
            self.block(f"Review ungültig: {legacy.strip(err)}")
        if files.get(rev, "status") == "bestanden":
            try:
                legacy.run("pflege.py", "sammeln", self.proj, rev)
            except Exception:  # noqa: BLE001 - collecting care items never blocks the stop
                pass
