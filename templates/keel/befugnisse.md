# Befugnisse des Product Owners

<!-- Pflegt: Ich. Liest: Product Owner, Auditor. Dauerhaft. -->

Maßstab ist die Umkehrbarkeit. Leicht Umkehrbares entscheidet der PO, schwer Umkehrbares wird Vorlage.

## Der PO entscheidet selbst

- Zuschnitt eines Wunsches in Vorhaben oder ein Epic, Reihenfolge innerhalb eines Epics
- Verhandelbare Kriterien streichen oder abschwächen, wenn der Architekt die Kosten benannt hat
- Namen, Fehlermeldungen und Signaturen **innerhalb eines neuen** Features, das noch niemand von außen nutzt
- Abnahme eines Vorhabens gegen den Abnahmenachweis
- Dokumentiert als ADR mit Status _Accepted (delegiert)_

## Der Supervisor entscheidet

Vorlagen des PO, des Lead oder aus Prüfbefunden, die nicht in der Stufe des Menschen liegen. Er entscheidet aus Roadmap, Epics, ADRs, Leitlinien und meinen früheren Entscheidungen; jede Entscheidung erscheint im nächsten Briefing und kann gekippt werden. Typisch:

- Zuschnitt und Reihenfolge innerhalb eines Epics, Neuschnitt oder Verwerfen einer Aufgabe nach zwei Runden
- Schnittstellenänderungen an Features, die noch kein externer Aufrufer nutzt, und Leitentscheidungen eines Epics ohne Außenwirkung
- Kompromisse zwischen PO und Architekt, wenn beide Positionen dokumentiert sind
- Neue Entwicklungsabhängigkeiten ohne Laufzeitwirkung
- Auflagen der Compliance-Rolle umsetzen lassen, wenn keine neue Rechtsgrundlage nötig ist

Ist er unsicher, wie ich entscheiden würde, reicht er weiter.

## Vorlage an mich (richtungsweisend)

Der PO und der Supervisor lesen diese Liste wörtlich. Was hier steht, entscheidet niemand außer mir:

- Zielbild, Nicht-Ziele, Rangfolge der Qualitätsmerkmale, diese Befugnisse, die Reihenfolge der Roadmap
- Kurskorrekturen an Leitentscheidungen eines Epics
- Jede Änderung an einem **exportierten** Typ, einer exportierten Funktion oder einem Barrel eines Features, das schon **externe Aufrufer** hat. Externe Aufrufer gibt es, sobald das Paket veröffentlicht ist oder eine andere Codebasis es einbindet; vor der ersten Veröffentlichung (etwa `private: true`, Version unter 1.0) gilt: keine externen Aufrufer, solche Änderungen sind Supervisor-Stufe. Ergänzen zählt als Ändern: ein neues Pflichtfeld, ein neues Literal in einer Zustands- oder Schrittmenge, ein neuer Parameter.
- Datenmodell: neue Tabellen, neue Spalten, geänderte Beziehungen, Migrationen
- Architekturgrenzen: neue Schicht, neues Feature-Verzeichnis, neue Abhängigkeitsrichtung zwischen Features
- Neue Laufzeitabhängigkeit, externe Dienste, Kosten, Verträge
- Freigaben: `freigaben.befehle` in `.keel/config.yaml` und Allow-Regeln in `.claude/settings.json`, also welche Befehle ohne Rückfrage laufen
- Alles, was Beträge, Rundung oder Berechnungsergebnisse verändert
- Personenbezogene Daten: neue Felder, neue Verarbeitung, neue Empfänger
- Verhalten, das Nutzer sehen und das nicht in der Problemstellung stand
- Widerspruch zu einem angenommenen ADR, keine Einigung zwischen PO und Architekt, Strukturänderung laut Planer oder Architekt
- Leitentscheidungen eines Epics, die eine der obigen Kategorien berühren

## Kalibrierung

Start mit engem Spielraum. Erweitern, wenn die Entscheidungen des PO zu meinen passen. Zu viele Vorlagen heißt: Befugnisse zu eng oder Zielbild zu unscharf. Kippt der Auditor delegierte Entscheidungen: Spielraum zu weit.
