# Befugnisse des Product Owners

<!-- Pflegt: Ich. Liest: Product Owner, Auditor. Dauerhaft. -->

Maßstab ist die Umkehrbarkeit. Leicht Umkehrbares entscheidet der PO, schwer Umkehrbares wird Vorlage.

## Der PO entscheidet selbst

- Zuschnitt eines Wunsches in Vorhaben oder ein Epic, Reihenfolge innerhalb eines Epics
- Verhandelbare Kriterien streichen oder abschwächen, wenn der Architekt die Kosten benannt hat
- Namen, Fehlermeldungen und Signaturen **innerhalb eines neuen** Features, das noch niemand von außen nutzt
- Abnahme eines Vorhabens gegen den Abnahmenachweis
- Dokumentiert als ADR mit Status _Accepted (delegiert)_

## Vorlage an mich

Der PO liest diese Liste wörtlich. Was hier nicht steht, entscheidet er. Deshalb konkret:

- Jede Änderung an einem **exportierten** Typ, einer exportierten Funktion oder einem Barrel eines Features, das schon abgenommen ist. Ergänzen zählt als Ändern: ein neues Pflichtfeld, ein neues Literal in einer Zustands- oder Schrittmenge, ein neuer Parameter.
- Datenmodell: neue Tabellen, neue Spalten, geänderte Beziehungen, Migrationen
- Architekturgrenzen: neue Schicht, neues Feature-Verzeichnis, neue Abhängigkeitsrichtung zwischen Features
- Neue Laufzeit- oder Entwicklungsabhängigkeit
- Alles, was Beträge, Rundung oder Berechnungsergebnisse verändert
- Personenbezogene Daten: neue Felder, neue Verarbeitung, neue Empfänger
- Verhalten, das Nutzer sehen und das nicht in der Problemstellung stand
- Widerspruch zu einem angenommenen ADR, keine Einigung zwischen PO und Architekt, Strukturänderung laut Planer oder Architekt
- Leitentscheidungen eines Epics, die eine der obigen Kategorien berühren

## Kalibrierung

Start mit engem Spielraum. Erweitern, wenn die Entscheidungen des PO zu meinen passen. Zu viele Vorlagen heißt: Befugnisse zu eng oder Zielbild zu unscharf. Kippt der Auditor delegierte Entscheidungen: Spielraum zu weit.
