---
nummer: 0012
titel: Zwei Befehle, Fälligkeiten aus dem Zustand, Gates nur bei genug Betrieb
status: Accepted
datum: 2026-09-22
entscheider: Ich
supersedes:
hypothese: Der Mensch benutzt im Alltag nur /keel:start und /keel:stop; kein Audit, Coach- oder Architekturlauf wird vergessen, und keiner läuft ohne genug Betrieb dazwischen
---

# 0012: Zwei Befehle, Fälligkeiten aus dem Zustand, Gates nur bei genug Betrieb

## Kontext

xXExceptionXx will sich nicht zehn Befehle merken und wann sie fällig sind. Das System soll leiten: Was fällig ist, ergibt sich aus dem Zustand des Projekts, und ein fälliger Lauf wird erzwungen, aber nur, wenn genug Betrieb stattgefunden hat.

## Entscheidung

- `scripts/due.py` leitet Fälligkeiten aus Artefakten ab: Briefing (Supervisor-Entscheidungen, Eskalationen, Kurskorrektur), Tagesabschluss (Arbeit eines Vortags ohne Tag), Audit (Tag ohne Prüfbericht), Coach (Tage seit dem letzten Lauf **und** Rollenläufe seitdem über den Schwellen), Architektur-Wochenrunde (Tage **und** Commits). Schwellen unter `faelligkeiten` in `.keel/config.yaml`.
- Harte Fälligkeiten sperren per Hook alle Rollen außer der, die sie erledigt; der SessionStart-Hook nennt sie beim Öffnen jeder Session.
- `/keel:start` arbeitet sie in fester Reihenfolge ab, wird zum Briefing, wenn eines aussteht, und geht sonst in den Tagesstart und das nächste Vorhaben über. `/keel:stop` ist Tagesabschluss plus Audit plus Ausblick. Die übrigen Befehle bleiben als Bausteine und für den gezielten Einsatz.
- Der Betriebs-Wrapper ruft `/keel:start` wiederholt und meldet, wenn ein Mensch gebraucht wird.

## Folgen

- Ein vergessener Tagesabschluss wird am nächsten Morgen nachgeholt, mit dem Datum des letzten Commits.
- Schwellen sind Korridore der Lernschleife: Läuft der Coach zu oft oder zu selten, schlägt er selbst die Anpassung vor.
