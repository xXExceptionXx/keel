---
nummer: 0014
titel: Helfer-Skill statt Proxy-Rolle, Beobachter ohne Befugnisse
status: Accepted
datum: 2026-09-26
entscheider: Ich
supersedes:
hypothese: Der Mensch braucht in den ersten Wochen keine zweite Aufsicht über keel, sondern eine Erklärung des Stands auf Abruf; /keel:hilfe senkt die Zahl der Sessions, in denen er raten muss, was fällig ist, auf null, und Motor-Befunde erreichen das Plugin-Repo als Issues statt im Gespräch verloren zu gehen
---

# 0014: Helfer-Skill statt Proxy-Rolle, Beobachter ohne Befugnisse

## Kontext

Für die Einführung in einem echten Projekt stand ein „Stützräder“-Modus zur Debatte: eine Proxy-Session (Fable oder Opus) über keel, die den Betrieb beaufsichtigt, kleine Korrekturen am Plugin sofort einarbeitet und Vorlagen durchreicht. Die Diskussion hat den Proxy Schritt für Schritt entkernt: Er darf keine Entscheidungen treffen, weil sonst der Supervisor Leitlinien aus Entscheidungen destilliert, die nicht der Mensch getroffen hat, und der Coach eine Kalibrierung misst, die nie stattfand. Er darf die Lead-Session nicht übernehmen, weil es genau einen Menschen im Kreislauf geben soll und die Vorlage auf ihn wartet. Er darf nicht zwischen Mensch und Supervisor vermitteln, weil Paraphrase Einfluss ist und das Briefing ohnehin in der Hauptsession auf dem Supervisor-Modell läuft. Was bleibt, ist „jemand, der den Stand versteht und erklärt“. Das ist keine Rolle.

Den Coach dafür zu erweitern wurde verworfen: Er ist ein Subagent und kann nicht im Gespräch antworten; er soll selten und teuer bleiben (Fälligkeit nach Tagen und Rollenläufen, Hypothesen, höchstens drei Vorlagen); und er misst, ohne zu hören, was man ihm erzählt.

## Entscheidung

- **`/keel:hilfe`** ist eine Skill der Hauptsession, keine Rolle. Sie stellt die Lage aus dem Zustand her (`scripts/lage.py`: Fälligkeiten, Vorhaben und Epics, offene Vorlagen, Ereignisse der letzten 24 Stunden nach Art und Grund gruppiert, Reste in den Zustandsdateien, Plugin-Versionen), erklärt sie in fünf Zeilen, nennt den einen nächsten Befehl und beantwortet Fragen aus Dateien, Ereignissen und Rollen-Transkripten.
- **Beobachter ohne Befugnisse.** Sie entscheidet nichts, startet keine Rolle, ändert weder Code noch Inhaltsartefakte noch die Mechanik im Projekt. Ein Hook markiert die Session beim Aufruf und sperrt darin jeden Rollenstart. Für eine Vorlage erklärt sie den Zusammenhang und verweist ins Briefing.
- **Drei Schreibrechte, jedes nach einem Ja des Menschen:** Reste der Zustandsdateien aufräumen (`lage.py --clean`), einen Hinweis für den Coach unter `.keel/work/hinweise/` ablegen, einen Motor-Befund als Issue im Plugin-Repo anlegen (`motor.repo` in `.keel/config.yaml`).
- **Der Coach liest die Hinweise** als weitere Quelle und bestätigt oder entkräftet jeden im Bericht mit Beleg. Er übernimmt sie nicht.
- **Motor-Reparaturen finden im Plugin-Repo statt**, nie im Projekt. Das Issue ist der Kanal.
- **Jede Ablehnung, die den Menschen erreicht** (Fälligkeits-Gate, Doppelstart, Modell-Gate, SessionStart-Hinweis), nennt `/keel:hilfe` als nächsten Schritt. Das ist der eine Befehl für „ich weiß nicht, was los ist“.
- Nebenbefund derselben Prüfung: Die vier Zustandsdateien je Rollenlauf wurden nie gelöscht (307 Dateien aus 77 Läufen im Beispiel). `agent-stop` löscht sie jetzt beim Beenden, `/keel:stop` räumt Reste abgebrochener Läufe auf, und `deny()` zeichnet Ablehnungen als Ereignis auf, damit die Lage sie zeigen kann.

## Folgen

- Es gibt weiterhin genau eine Aufsicht (Supervisor) und genau einen Entscheider (Mensch). Der Helfer verschiebt nichts daran.
- Das „Stützräder“-Bedürfnis wird durch Erklärung statt durch Eingriff bedient. Ob das reicht, zeigt sich daran, wie oft der Mensch trotzdem eine Session im Plugin-Repo öffnet, um etwas nachzusehen.
- Hinweise sind ein neuer Eingang in die Lernschleife, der nicht aus Kennzahlen kommt. Der Coach muss sie als Frage behandeln, sonst wird er zum Sprachrohr; die Regel steht in seinem Prompt, und `einwaende_supervisor` bleibt der Korridor gegen Nach-dem-Mund-Reden.
