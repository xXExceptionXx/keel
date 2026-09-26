---
nummer: 0015
titel: Modell je Rollenlauf mitschreiben, Modellwechsel erkennen, Coach vorziehen
status: Accepted
datum: 2026-09-26
entscheider: Ich
supersedes:
hypothese: Ein Modellwechsel wird am Tag seines ersten Rollenlaufs als Hinweis sichtbar statt erst beim nächsten Monatslauf des Coachs; nach spätestens zehn Läufen auf dem neuen Modell liegt ein Coach-Bericht mit Vergleich je Rolle vor, und die Umstellung von Rollen oder Supervisor-Modell geschieht über eine Vorlage mit Hypothese statt unbemerkt
---

# 0015: Modell je Rollenlauf mitschreiben, Modellwechsel erkennen, Coach vorziehen

## Kontext

Opus 5.5 war seit einigen Tagen verfügbar, und keel hat davon nichts bemerkt. Nur der Supervisor hat ein festes Modell (`agents/supervisor.md`, `supervisor.model`). Alle anderen Rollen laufen auf dem Modell der Session und wechseln still mit, sobald jemand die Session umstellt. Der Coach sollte laut ADR 0013 bei einem Modellwechsel alle Schutzmaßnahmen auf Rückbau prüfen, konnte das aber nicht: Kein Ereignis hielt fest, welches Modell einen Rollenlauf ausgeführt hat, und er wird erst nach 30 Tagen und 40 Rollenläufen fällig. Risiko 12 im Register war damit nur auf dem Papier abgedeckt.

## Entscheidung

1. **Modell mitschreiben.** `agent_stop` trägt `model`, das Modell aus dem Transcript des Subagents; `agent_start` trägt `lead_model`, das Modell der Lead-Session. Ältere Ereignisse ohne `model` lesen es aus dem Transcript, solange es existiert.
2. **Wechsel erkennen, je Rolle.** `scripts/models.py` meldet einen Wechsel, wenn eine Rolle zuletzt auf einem anderen Modell lief als überwiegend davor. Ein einzelner Lauf dazwischen, etwa ein Fallback bei Überlast, ist kein Wechsel. Ein Wechsel bleibt offen, bis ein Coach-Bericht das neue Modell unter `modell_geprueft` nennt.
3. **Hinweis sofort, Coach mit Daten.** `due.py` zeigt einen offenen Wechsel als weichen Hinweis beim Sessionstart. Sobald `faelligkeiten.coach_nach_modellwechsel_rollenlaeufe` Läufe (Standard 10) auf dem neuen Modell vorliegen, wird der Coach hart fällig, unabhängig von `coach_tage`. Direkt nach dem Wechsel hätte er nichts zu vergleichen.
4. **Vergleich je Modell.** `metrics.py` teilt die Ergebnisse der Rollenläufe nach Modell: Läufe, blockierte Übergaben, Budget erschöpft, Tokens pro Lauf, und für das Modell des Entwicklers Reviews mit Befunden und Review-Runden.
5. **Coach bewertet, Hook hält ihn an.** Der Coach schreibt bei einem Wechsel mit genug Läufen den Abschnitt „Modellzuordnung“ und setzt `modell_geprueft`; der Stop-Hook lässt ihn vorher nicht gehen. Er prüft auch das Umfeld auf neue Modelle, die im Projekt noch nicht laufen. Änderungen (Rolle zurück, Supervisor-Modell, `budget.context_window`, Umstieg) bleiben Vorlagen mit Hypothese.

Keine Websuche beim Sessionstart: langsam, abhängig vom Netz, und Webinhalte sind Daten, keine Anweisungen. Keine Rückfrage beim Start: Der Mensch entscheidet über eine Vorlage mit Begründung, nicht aus dem Stegreif.

## Bekannte Preise, bewusst gezahlt

- Die Modellwahl je Rolle bleibt, wie sie ist: Supervisor fest, alle anderen auf dem Session-Modell. keel sieht den Wechsel jetzt, steuert ihn aber nicht. Wie Rollen künftig ihr Modell bekommen, beschreibt der Vorschlag in ADR 0016.
- Der Vergleich ist grob: Aufgaben nach dem Wechsel sind andere als davor. Der Coach deutet die Zahlen, er beweist nichts.
- Ein Wechsel, der vor diesem ADR geschah und dessen Transcripts gelöscht sind, bleibt unsichtbar.
