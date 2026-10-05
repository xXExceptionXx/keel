"""Decisions taken in kern-befunde.md (2026-10-05): objections count only where the human deviated from the
Supervisor's recommendation (P1); a briefing counts as a run of the Supervisor for model switches (P2)."""
import json

from harness import ContractTest, project, write

DAY = "2026-10-01"


def decided(p, name, abweichung):
    write(p / ".keel" / "decisions" / "done" / f"{name}.md",
          f"---\ntyp: vorlage\ntitel: {name}\ndatum: {DAY}\nstatus: entschieden\nentscheider: Mensch\n"
          f"eskaliert: Supervisor\nempfehlung: A\nentscheidung: B\nabweichung: {abweichung}\nentschieden: {DAY}\n---\n")


class ObjectionFigureTest(ContractTest):
    def figure(self, p):
        r = self.script("metrics.py", p, "--json", proj=p)
        self.assertIn(r.rc, (0, 3), r)
        row = next(k for k in r.json["kennzahlen"] if k["kennzahl"] == "einwaende_bei_abweichung_prozent")
        return row["wert"], row["status"]

    def test_without_a_deviation_there_is_nothing_to_object_to(self):
        p = project()
        decided(p, "v-folgt", "nein")
        self.assertEqual(self.figure(p), (None, "n/a"))

    def test_a_silent_supervisor_on_a_deviation_breaks_the_corridor(self):
        p = project()
        decided(p, "v-weicht-ab", "ja")
        self.assertEqual(self.figure(p), (0, "verletzt"))
        write(p / ".keel" / "adr" / "0001-x.md", "---\nnummer: 0001\ntitel: x\nstatus: Accepted\nentscheider: Mensch\n"
                                                 "---\n# x\n\n## Einwand des Supervisors\n\nKostet zwei Wochen.\n")
        self.assertEqual(self.figure(p), (100, "ok"))


class BriefingRunTest(ContractTest):
    def test_briefings_count_as_supervisor_runs(self):
        p = project()
        rt = self.runtime(p)
        rt.mkdir(parents=True, exist_ok=True)
        lines = [{"event": "agent_stop", "ts": f"2026-09-2{i}T08:00:00Z", "role": "supervisor", "model": "alt",
                  "agent_id": f"a{i}"} for i in range(3)]
        lines += [{"event": "briefing_geprueft", "ts": f"2026-10-0{i}T07:00:00Z", "model": "neu",
                   "session_id": f"s{i}"} for i in range(1, 6)]
        (rt / "events.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
        r = self.script("models.py", p, "--json", proj=p)
        self.assertEqual(r.rc, 0, r)
        self.assertEqual(r.json["aktuell_je_rolle"]["supervisor"], "neu")
        [switch] = r.json["offene_wechsel"]
        self.assertEqual((switch["modell"], switch["laeufe"]), ("neu", 5))
