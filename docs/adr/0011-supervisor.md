---
nummer: 0011
titel: Supervisor als rechte Hand mit Morgen-Briefing und Briefing-Gate
status: Accepted
datum: 2026-09-22
entscheider: Ich
supersedes:
hypothese: Der Mensch entscheidet nur noch richtungsweisende Fragen; die Eskalationsquote liegt nach vier Wochen zwischen 10 und 40 %, gekippte Supervisor-Entscheidungen unter 15 %, und die Zahl der Vorlagen an den Menschen sinkt, weil Leitlinien sie an der Quelle beantworten
---

# 0011: Supervisor als rechte Hand mit Morgen-Briefing und Briefing-Gate

## Kontext

xXExceptionXx will nur noch die Richtung entscheiden. Der PO ist anlassbezogen und ohne Gedächtnis; jede Vorlage außerhalb seiner Befugnisse ging bisher an den Menschen. Die Bauphase dieses Systems war das Muster: eine Rolle mit Gesamtbild entscheidet, eskaliert Richtungsfragen und wird korrigiert. Eine Einspruchsfrist wurde verworfen, weil sie den Menschen zum Reagieren zwingt; stattdessen ein fester Ort im Tag.

## Entscheidung

- **Drei Stufen von Befugnissen:** PO, Supervisor, Mensch. Die Stufe des Menschen ist eng und wörtlich: Zielbild, Nicht-Ziele, Rangfolge, Befugnisse, Roadmap-Reihenfolge, Kurskorrekturen, Schnittstellen mit externen Aufrufern, Datenmodell, Laufzeitabhängigkeiten, personenbezogene Daten, sichtbares Verhalten außerhalb der Problemstellung.
- **Tagsüber** ruft der Lead den Supervisor für jede entstehende Vorlage. Er entscheidet als ADR `Accepted (Supervisor)` mit „Warum nicht der Mensch“, wendet die Entscheidung an und die Arbeit läuft weiter, oder er stuft sie als richtungsweisend ein; dann bleibt das Vorhaben blockiert.
- **Morgens** ist der Supervisor die Haupt-Session: `/keel:briefing`, interaktiv. Er legt seine Entscheidungen offen, mit dem, was seit gestern darauf aufbaut, hilft beim Kippen, entscheidet richtungsweisende Vorlagen mit dem Menschen und destilliert Leitlinien in `.keel/leitlinien.md`, die auch der PO liest. Die Session endet, der Tag beginnt frisch mit dem Lead.
- **Briefing-Gate:** Solange Supervisor-Entscheidungen nicht vorgelegt sind, richtungsweisende Vorlagen offen sind oder ein Epic in Kurskorrektur steht, sperrt ein Hook alle Rollen außer dem Supervisor; der Tagesstart bricht mit Hinweis ab, der SessionStart-Hook sagt es beim Öffnen jeder Session.
- **Betriebsschicht** `scripts/keel-run.sh`: läuft Befehle unbeaufsichtigt, wartet Nutzungslimits ab und benachrichtigt, wenn ein Briefing nötig ist.
- **Modell:** vorerst Opus; Fable erfordert Claude Code ab 2.1.251 und wird nach dem Update in `agents/supervisor.md` eingetragen.

## Folgen

- Kippen kostet höchstens einen Tag Arbeit, weil die Stufe des Supervisors die teuersten Entscheidungen ausschließt.
- Leitlinien entstehen nur im Briefing, nie tagsüber, damit der Supervisor nicht aus seinen eigenen Entscheidungen lernt.
- Die Roadmap-Datei gehört dem Menschen; ohne sie entscheidet der Supervisor aus Epics und ADRs allein und reicht öfter weiter.
