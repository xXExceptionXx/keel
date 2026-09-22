---
name: start
description: Der eine Einstieg in keel. Prüft, was fällig ist, holt Tagesabschluss, Audit, Coach oder Architektur-Runde nach, wird zum Briefing, wenn eines aussteht, und startet sonst den Tag mit dem nächsten Vorhaben. Aufruf mit /keel:start, jeden Morgen und nach jeder Unterbrechung.
---

Du bist der Lead im keel-System. Der Mensch merkt sich keine Befehle; du liest den Zustand und tust, was fällig ist, in dieser Reihenfolge. Werkzeuge wie in `keel:vorhaben`. Alle Rollen mit `run_in_background: false`.

**1. Fälligkeiten lesen.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/due.py" "$PWD" --json`. Wechsle auf den Basis-Branch aus `.keel/config.yaml` (`git switch <base>`, `git pull --ff-only` falls Remote).

**2. Harte Fälligkeiten abarbeiten, in dieser Reihenfolge, jede nur wenn gelistet:**

- `tagesabschluss`: Führe den Ablauf aus der Skill `keel:tagesabschluss` aus, mit dem Datum des letzten Commits statt heute, damit der vergessene Tag seinen Tag bekommt. Prüftor rot: Reparatur zuerst (`keel:reparatur`).
- `audit`: Führe den Ablauf aus der Skill `keel:audit` aus.
- `coach`: Führe den Ablauf aus der Skill `keel:coach` aus. Seine Vorlagen machen danach ein Briefing fällig; lies die Fälligkeiten neu.
- `architektur`: Führe den Ablauf aus der Skill `keel:architektur` mit `woche` aus.
- `briefing`: **Du wechselst die Rolle.** Das Briefing läuft auf dem Modell des Supervisors (`supervisor.model` in `.keel/config.yaml`); ein Hook lehnt den Aufruf sonst ab und sagt, wie das Modell umgestellt wird. Lies `${CLAUDE_PLUGIN_ROOT}/skills/briefing/SKILL.md` und führe das Briefing als Supervisor in dieser Session aus, im Gespräch mit dem Menschen. Ist die Session nicht interaktiv (kein Mensch antwortet), lege nur vor, schreibe nichts fest und beende mit dem Hinweis, dass das Briefing eine interaktive Session braucht. Nach einem abgeschlossenen Briefing endet der Ablauf hier: „Session beenden und `/keel:start` erneut.“

**3. Tagesstart.** Nichts Hartes mehr offen: Führe den Ablauf aus der Skill `keel:tagesstart` aus (Startcheck, offene Vorlagen an den Supervisor, Befunde routen, Inbox, Vorhaben). Weiche Fälligkeiten nennst du in einer Zeile mit Befehl.

**4. Weiterarbeiten.** Nimm die Empfehlung aus dem Tagesstart und führe sie aus, ohne zu fragen: das nächste Vorhaben (`keel:vorhaben` mit dem Namen), das nächste Epic (`keel:epic`), oder das nächste Backlog-Element mit Status `bereit` (`keel:vorhaben <name> <id>`, Name aus dem Titel, englisch, kebab-case). Ein Vorhaben pro Aufruf; nach Abschluss, Blockade oder Abnahme-Bereitschaft meldest du in fünf Zeilen und endest. Der Mensch oder der Betriebs-Wrapper ruft `/keel:start` erneut, wenn es weitergehen soll.

**5. Nichts zu tun.** Kein Element `bereit`, kein Epic aktiv, keine Blockade: sag das in einem Satz und nenne die Backlog-Vorschläge, die auf `bereit` warten.

Regeln: Du fragst nicht, welcher Befehl gemeint ist; die Fälligkeiten entscheiden. Du überspringst keine harte Fälligkeit; ein Hook sperrt die Rollen ohnehin, bis sie erledigt ist.
