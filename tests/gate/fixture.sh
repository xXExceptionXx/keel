#!/usr/bin/env bash
# fixture.sh <dir> [normal|briefing|tagesabschluss|audit]: a keel project covering every entry condition of agent-gate
set -e
d="$1"; rm -rf "$d"; mkdir -p "$d"; cp -r "$(dirname "$0")/../../templates/keel" "$d/.keel"
cd "$d"; git init -q; git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
w=.keel/work
plan() { printf -- "---\ntyp: plan\nvorhaben: %s\nstatus: %s\n%b---\n# Plan %s\n" "$2" "$3" "${4:-}" "$1" > $w/plans/$1.md; }
task() { printf -- "---\ntyp: aufgabe\nid: %s\nvorhaben: V9\ntitel: T %s\nstatus: %s\n%b---\n# Aufgabe %s\n%b" "$1" "$1" "$2" "${3:-}" "$1" "${4:-}" > $w/tasks/$1.md; }
plan p-entwurf V1 entwurf "bewertung: stufe-2\n"
plan p-entwurf-nobew V2 entwurf
plan p-problem V3 problemstellung
plan p-atb V4 abnahmetests-bereit
plan p-nach V5 nacharbeit
plan p-geplant V6 geplant "aufgaben: [T-geplant]\n"
plan p-struktur V7 strukturaenderung
plan p-abn V8 abnahme-bereit
plan p-abnrot-noacc V10 abnahme-rot
plan p-integriert V11 integriert
printf -- "---\ntyp: abnahme\nstatus: gruen\n---\n" > $w/acceptance/p-abn.md
task T-geplant geplant
task T-neu neuschnitt "" "\n## Klärung\nFrage\n"
task T-neu-noklar neuschnitt
task T-tb tests-bereit "tests: [a.py]\ndateien: [b.py]\n"
task T-tb-empty tests-bereit "tests: []\ndateien: [b.py]\n"
task T-nach nacharbeit "tests: [a.py]\ndateien: [b.py]\n"
task T-review review "review_runde: 1\n"
task T-review-norunde review
task T-rep reparatur
printf -- "---\ntyp: aufgabe\nid: T-rep-nach\nvorhaben: R\ntitel: Reparatur\nstatus: nacharbeit\ntests: []\ndateien: []\n---\n" > $w/tasks/T-rep-nach.md
task T-comp fertig-gemeldet "compliance: pruefen\n"
task T-comp-noscan fertig-gemeldet "compliance: pruefen\n"
task T-fertig fertig
printf -- "---\ntyp: compliance\n---\n" > $w/compliance/T-comp.scan.md
ep() { printf -- "---\ntyp: epic\nepic: %s\ntitel: E\nstatus: %s\nbacklog: B1\n---\n" "$1" "$2" > $w/epics/$1.md; }
ep e-skizze skizze; ep e-bewertet bewertet; ep e-leit leitentscheidungen-offen; ep e-aktiv aktiv
vl() { printf -- "---\ntyp: vorlage\ntitel: %s\nvon: PO\ndatum: 2026-09-20\nstatus: %s\n%b---\n" "$1" "$2" "${3:-}" > .keel/decisions/pending/$1.md; }
vl v-offen offen
vl v-entschieden entschieden
[ "${2:-}" = briefing ] && vl v-esk offen "eskaliert: Supervisor\n"
if [ "${2:-}" = tagesabschluss ]; then  # work from yesterday without a day tag
  echo x > code.txt; git add code.txt
  y="$(python3 -c 'import datetime; print((datetime.datetime.now() - datetime.timedelta(days=1)).replace(microsecond=0).isoformat())')"
  GIT_COMMITTER_DATE="$y" git -c user.email=t@t -c user.name=t commit -q -m work --date "$y"
fi
if [ "${2:-}" = audit ]; then  # a day tag without an audit report
  echo x > code.txt; git add code.txt; git -c user.email=t@t -c user.name=t commit -q -m work; git tag "day-$(date +%Y-%m-%d)"
fi
exit 0
