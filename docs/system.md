# keel auf einen Blick

Sieben Sichten auf dasselbe System, Stand 0.12. Alle Diagramme sind Mermaid und rendern direkt auf GitHub; die Quelle ist diese Datei.

## 1. Rollen und Beziehungen

Wer entscheidet, wer taktet, wer prüft. Durchgezogen: Aufruf oder Auftrag. Gestrichelt: Bericht oder Vorlage. Der Mensch spricht im Alltag nur mit dem Supervisor, im Morgen-Briefing, und schreibt Backlog-Einträge.

```mermaid
flowchart TD
    ICH(["Ich<br/>Zielbild, Rangfolge, Befugnisse<br/>Roadmap, Backlog-Einträge, Richtung"])
    SUP["Supervisor<br/>rechte Hand, Gesamtbild<br/>entscheidet Vorlagen seiner Stufe<br/>Briefing morgens"]
    AUD["Auditor<br/>täglich Diff, wöchentlich Gesamtstand"]
    COACH["Coach<br/>Kennzahlen, Hypothesen, Umfeld"]
    LEAD["Lead (Haupt-Session)<br/>/keel:start, /keel:stop<br/>taktet, aggregiert, urteilt nicht"]
    PO["PO<br/>Problemstellung, Epic-Skizze<br/>Abstimmung, Klärung, Abnahme"]
    ARC["Architekt<br/>Bewertung in 3 Stufen<br/>Epic-Bewertung nach Reichweite<br/>Bestandsaufnahme, Wochenrunde, Pflegeliste"]
    PLAN["Planer"]
    TEST["Tester"]
    DEV["Entwickler"]
    REV["Reviewer<br/>Schwelle, Nacharbeit als eigenes Delta"]
    COMP["Compliance<br/>Scan als Hook, Rolle bei Ermessen"]

    ICH <-->|Briefing, interaktiv| SUP
    ICH -->|Backlog-Eintrag| LEAD
    LEAD -->|Vorlage| SUP
    SUP -.->|richtungsweisend| ICH
    LEAD --> PO
    LEAD --> ARC
    PO <-.->|max. 2 Runden, vom Lead getaktet| ARC
    LEAD --> PLAN
    LEAD --> TEST
    LEAD --> DEV
    LEAD --> REV
    LEAD --> COMP
    AUD -.->|Prüfbericht| ICH
    COACH -.->|Coach-Bericht, Vorlagen mit Hypothese| ICH

    classDef human fill:#fff3cd,stroke:#b58900,color:#000
    classDef outside fill:#e8f4fd,stroke:#2b6cb0,color:#000
    classDef sup fill:#e6ffe6,stroke:#2f855a,color:#000
    class ICH human
    class AUD,COACH outside
    class SUP sup
```

Auditor und Coach stehen außerhalb der Befehlskette und ändern nichts außer ihrem Bericht. Der Supervisor entscheidet innerhalb seiner Stufe der Befugnisse und reicht richtungsweisende Fragen weiter; jede seiner Entscheidungen erscheint im nächsten Briefing und kann gekippt werden.

## 2. Zwei Befehle und die Fälligkeiten

`/keel:start` liest den Zustand und tut, was fällig ist. Harte Fälligkeiten sperren per Hook alle Rollen außer der, die sie erledigt. `/keel:hilfe` steht daneben als Beobachter: Es erklärt den Stand aus `lage.py` (Fälligkeiten, Vorhaben, Vorlagen, Ereignisse nach Grund, Reste), nennt den nächsten Befehl und darf nur mit Ja des Menschen Reste aufräumen, einen Hinweis für den Coach ablegen oder einen Motor-Befund als Issue melden. Jede Ablehnung, die den Menschen erreicht, verweist darauf (System-ADR 0014). `/keel:monitor` zeigt dieselbe Lage laufend als lokale Webseite, mit einem Ablaufdiagramm (aktiv, bereit, gesperrt), Ereignisstrom, einer Zeitleiste je Vorhaben und allen Übergaben als Dokumente, und schreibt ebenfalls nichts; mit `monitor.autostart: true` starten ihn die Startbefehle mit. Die Startbedingungen der Rollen stehen in `scripts/flow.py`, aus dem Gate und Monitor lesen (System-ADR 0017).

```mermaid
flowchart TD
    S["/keel:start"] --> D{"due.py<br/>was ist fällig?"}
    D -->|Arbeit ohne Tag| TA["Tagesabschluss nachholen<br/>Übergabenotiz, Belege prüfen, Tag"]
    TA --> D
    D -->|Tag ohne Prüfbericht| AU["Auditor"]
    AU --> D
    D -->|≥ 30 Tage und ≥ 40 Rollenläufe,<br/>oder Modellwechsel mit ≥ 10 Läufen| CO["Coach → Vorlagen"]
    CO --> D
    D -->|≥ 7 Tage und ≥ 10 Commits| AR["Architekt, Wochenrunde"]
    AR --> D
    D -->|Supervisor-Entscheidungen offen,<br/>Eskalationen, Kurskorrektur| BR(["Briefing mit dem Supervisor<br/>interaktiv, Modell des Supervisors<br/>Session endet danach"])
    D -->|nichts Hartes| TS["Tagesstart<br/>Startcheck, offene Vorlagen → Supervisor<br/>Befunde routen, Inbox"]
    TS --> V["nächstes Vorhaben oder Epic<br/>ein Vorhaben pro Aufruf"]
    V --> E["/keel:stop<br/>Tagesabschluss, Audit, Ausblick"]
    TS -. Startcheck rot .-> R["Reparatur auf fix/<ID>"] -.-> TS

    classDef human fill:#fff3cd,stroke:#b58900,color:#000
    class BR human
```

## 3. Ein Vorhaben von der Problemstellung bis zur Integration

Zustände des Plans. Der Mensch setzt keinen davon mehr selbst; der PO nimmt delegiert ab, der Mensch sieht es im Briefing.

```mermaid
stateDiagram-v2
    [*] --> entwurf: PO schreibt Problemstellung aus dem Backlog-Element
    entwurf --> entwurf: Architekt bewertet, PO stimmt ab (Runde 1, 2)
    entwurf --> problemstellung: Abstimmung einig, ggf. delegiertes ADR
    entwurf --> blockiert: keine Einigung, Vorlage → Supervisor → ggf. Mensch
    problemstellung --> abnahmetests_bereit: Tester schreibt Abnahmetests (rot)
    abnahmetests_bereit --> geplant: Planer schneidet Aufgaben
    abnahmetests_bereit --> strukturaenderung: Planer braucht Strukturänderung
    strukturaenderung --> abnahmetests_bereit: Architekt beantwortet
    strukturaenderung --> blockiert: ADR-Entwurf, Vorlage
    geplant --> in_arbeit: Aufgabenzyklus
    in_arbeit --> in_arbeit: je Aufgabe Tester, Entwickler, Compliance-Scan, Reviewer, Commit
    in_arbeit --> blockiert: zweiter Neuschnitt, Vorlage
    blockiert --> in_arbeit: Supervisor oder Mensch entscheidet
    in_arbeit --> abnahme_bereit: Abnahmetests grün
    in_arbeit --> abnahme_rot: Abnahmetests rot
    abnahme_rot --> nacharbeit: PO schreibt Nacharbeit
    abnahme_bereit --> abgenommen: PO nimmt ab (delegiert)
    abnahme_bereit --> nacharbeit: PO verlangt Nacharbeit
    nacharbeit --> geplant: Planer schneidet neue Aufgaben
    abgenommen --> integriert: Merge in die Basis, Abnahmetests werden Regression, Epic-Retrospektive
    integriert --> [*]
```

## 4. Der Aufgabenzyklus mit seinen Rückläufen

Der Weg nach vorn ist kurz. Entscheidend sind die Rückläufe, und die sind feste Übergaben.

```mermaid
stateDiagram-v2
    [*] --> geplant: Planer
    geplant --> tests_bereit: Tester schreibt Aufgabentests
    tests_bereit --> fertig_gemeldet: Entwickler, Prüftor und Compliance-Scan beim Beenden
    tests_bereit --> testeinspruch: Entwickler hält Test für falsch
    tests_bereit --> budget_erschoepft: Hook stoppt bei Aufrufen, Zeit oder Diff
    fertig_gemeldet --> compliance: Scan meldet pruefen oder vorlage
    compliance --> nacharbeit: Auflagen
    compliance --> review: frei
    compliance --> blockiert: Vorlage (neue Abhängigkeit, Rechtsgrundlage)
    fertig_gemeldet --> review: Scan frei, Lead setzt Runde +1
    review --> fertig: unter der Schwelle, Lead committet, Anmerkungen in die Pflegeliste
    review --> nacharbeit: über der Schwelle, Runde 1 oder Befunde sinken
    nacharbeit --> fertig_gemeldet: frischer Entwickler mit Befunden und Auflagen
    review --> blockiert_review: Befunde sinken nicht oder 4 Runden, Vorlage
    blockiert_review --> neuschnitt: Supervisor
    blockiert_review --> nacharbeit: Supervisor gibt Zusatzrunde
    testeinspruch --> neuschnitt
    budget_erschoepft --> neuschnitt
    neuschnitt --> klaerung: Planer fragt den PO
    klaerung --> neuschnitt: PO antwortet
    neuschnitt --> geplant: Planer schneidet neu, tests leer
    neuschnitt --> ersetzt: Planer ersetzt durch kleinere Aufgaben
    neuschnitt --> verworfen: Planer verwirft
    fertig --> [*]
    ersetzt --> [*]
    verworfen --> [*]
```

## 5. Epic: Leitentscheidungen vor dem ersten Vorhaben

Für große Themen. Der Architekt bewertet nach Reichweite, welche Entscheidung im ersten Vorhaben ein späteres wieder umstoßen müsste.

```mermaid
stateDiagram-v2
    [*] --> skizze: PO: Zielbild des Themas, Vorhaben-Liste, Leitfragen, Done-Condition
    skizze --> bewertet: Architekt: tragende Entscheidungen, Reichweite, Kosten der Umkehr
    bewertet --> aktiv: PO entscheidet in seiner Stufe (ADR delegiert)
    bewertet --> leitentscheidungen_offen: Vorlagen → Supervisor → richtungsweisend → Mensch
    leitentscheidungen_offen --> aktiv: entschieden, PO überführt in ADRs
    aktiv --> aktiv: Vorhaben 1..n, je Integration eine Retrospektive des Architekten
    aktiv --> kurskorrektur: Retrospektive: Leitentscheidung war falsch
    kurskorrektur --> aktiv: Mensch entscheidet im Briefing
    aktiv --> fertig: alle Vorhaben integriert, Done-Condition grün, PO nimmt ab
    fertig --> [*]
```

## 6. Was die Hooks um eine Rolle herum tun

Am Beispiel des Entwicklers. Jede Prüfung ist deterministisch und unabhängig vom Modell; blockiert wird mit dem konkreten Mangel. Welcher Status für welche Rolle und welchen Anlass nötig ist und welche Rollen eine harte Fälligkeit freigibt, liest agent-gate aus `scripts/flow.py`, derselben Tabelle, aus der der Monitor „bereit“ und „gesperrt“ ableitet. Ist sie nicht lesbar, startet keine Rolle. Allgemein gilt der Fehlervertrag aus System-ADR 0019: Kann ein Gate nicht prüfen, weil ein Werkzeug fehlt, ein Feld leer ist oder ein Hilfsskript abstürzt, blockiert es mit Meldung, statt durchzulassen; Beobachter wie Protokoll und Kontext-Alarm protokollieren den Fehler als `hook_error` und lassen weiterlaufen. `python3 -m unittest discover -s tests/contract` prüft die Hooks von außen gegen feste Sollwerte, `python3 -m unittest discover -s tests/unit -t .` den Kern selbst, `python3 tests/gate/run.py --against main` vergleicht das Gate mit einem früheren Stand.

Hooks und Skripte lesen und schreiben nicht selbst, sondern über das Paket `lib/keel` (System-ADR 0020). Die Schicht `store` ist die einzige Stelle für Pfade (Laufzeit-Ordner `<projekt>-<hash>` je Projekt), Frontmatter und Konfiguration (ein strikter Codec, der Unverständliches mit Datei und Zeile ablehnt), Ereignisse (tolerant, in UTC) und gemeinsame Dateien (atomar und unter Sperre). `bin/keel path` liefert den Hooks die Pfade, `bin/keel doctor` prüft Projekt und Rechner; `/keel:hilfe` zeigt das Ergebnis im Abschnitt „Gesundheit“.

```mermaid
sequenceDiagram
    participant L as Lead
    participant G as agent-gate (PreToolUse Agent)
    participant S as agent-start (SubagentStart)
    participant D as Entwickler
    participant T as tool-gate (PreToolUse)
    participant E as agent-stop (SubagentStop)

    L->>G: Agent keel:entwickler, "Aufgabe: V1-T02", Vordergrund
    G->>G: Fälligkeit offen? Rolle schon aktiv? Hintergrund?<br/>Aufgabe hat status tests-bereit, tests und dateien gefüllt?
    G-->>L: deny mit Grund (bei Verstoß)
    G->>S: Referenz V1-T02 geparkt
    S->>S: agent_id an V1-T02 gebunden, Zähler und Uhr auf 0
    loop jeder Werkzeugaufruf
        D->>T: Read, Edit, Bash …
        T->>T: Testdatei des Testers? Kennzahlen-Ordner?<br/>Aufrufe oder Zeit über dem Rollenbudget?
        T-->>D: deny mit Grund (bei Verstoß)
    end
    D->>E: fertig, Abschlussnachricht
    E->>E: höchstens 3 Zeilen? status fertig-gemeldet mit nachweis?<br/>Prüftor grün? Diff unter Grenze?<br/>Compliance-Scan: Secret blockiert, sonst compliance= frei|pruefen|vorlage
    E-->>D: block: weiterarbeiten mit Grund
    E-->>L: Rückkehr mit einer Zeile
```

## 7. Supervisor-Schleife, Lernschleife, Branches

Links: Vorlagen laufen tagsüber über den Supervisor, morgens legt er vor. Mitte: die Lernschleife. Rechts: `main` fasst das System nie an, außer es ist die konfigurierte Basis.

```mermaid
flowchart LR
    subgraph Supervisor
        VL["Vorlage<br/>PO, Lead, Architekt,<br/>Compliance, Befund"]
        SD{"Stufe?"}
        ADR1["ADR Accepted (Supervisor)<br/>angewendet, Arbeit läuft weiter"]
        ESK["eskaliert: richtungsweisend<br/>Vorhaben bleibt blockiert"]
        BRF(["Briefing morgens<br/>bestätigen oder kippen<br/>Einwand ist Pflicht<br/>Leitlinien"])
        VL --> SD
        SD -->|Supervisor| ADR1 --> BRF
        SD -->|Mensch| ESK --> BRF
        BRF -->|Leitlinien| VL
    end
    subgraph Lernschleife
        H["Hooks: events.jsonl<br/>außerhalb des Repos"]
        AR["Artefakte, Git-Log"]
        M["metrics.py<br/>Korridore"]
        CO["Coach<br/>Hypothesen, Umfeld,<br/>Einwände nachhalten"]
        SA["System-ADR im Plugin"]
        H --> M
        AR --> M
        M --> CO -->|Vorlagen| BRF
        BRF --> SA
        SA -. nächster Lauf prüft Hypothese .-> CO
    end
    subgraph Branches
        MAIN[("main<br/>manueller Schritt des Menschen")]
        BASE[("Basis: develop / staging<br/>git.base_branch")]
        F["feature/name<br/>ein Commit je Aufgabe<br/>Trailer Keel-Task"]
        X["fix/R-Datum<br/>Reparatur"]
        BASE --> F -->|Merge nach PO-Abnahme| BASE
        BASE --> X -->|Merge nach Review| BASE
        BASE -. Mensch .-> MAIN
    end
    classDef human fill:#fff3cd,stroke:#b58900,color:#000
    class BRF human
```

## 8. Wer schreibt was, wer liest was

| Artefakt | Schreibt | Liest | Prüft an der Grenze |
| --- | --- | --- | --- |
| `.keel/zielbild.md`, `qualitaetsmerkmale.md`, `befugnisse.md` (drei Stufen), `roadmap.md` | Ich | Supervisor, PO, Architekt, Auditor, Coach | – |
| `.keel/leitlinien.md` | Supervisor, nur im Briefing | Supervisor, PO | – |
| `.keel/backlog.md` oder GitHub Issues | Ich (Reihenfolge), PO (Vorhaben, Folge-Elemente), Tagesstart (Befunde) | PO, Auditor, Coach, nur über `backlog.py` | – |
| `.keel/work/epics/<name>.md` (+ `.bewertung.md`) | PO, Architekt | PO, Architekt, Lead, Supervisor | agent-stop |
| `.keel/work/plans/<name>.md` | PO, Architekt (Bewertung), Tester, Planer, Lead (Status) | alle Rollen des Vorhabens | agent-gate, agent-stop |
| `.keel/work/tasks/<ID>.md` | Planer, Tester, Entwickler, Lead, Compliance-Scan | Tester, Entwickler, Reviewer, Compliance, Auditor | agent-gate, agent-stop |
| `.keel/work/reviews/`, `compliance/` | Reviewer, Compliance | Entwickler (Nacharbeit), Auditor, metrics.py | agent-stop (Schwelle und Trend über `review.py`) |
| `.keel/work/pflege.md` | agent-stop (Anmerkungen bestandener Reviews), Architekt (Sichtung) | Architekt, metrics.py | agent-stop (höchstens n Pflegeaufgaben je Wochenrunde) |
| `.keel/work/acceptance/<name>.md` | Lead | PO, Auditor | – |
| `.keel/work/handoff/<Datum>.md` | Lead (Tagesabschluss) | Tagesstart, Auditor | check_references.py |
| `.keel/work/audit/`, `architektur/` | Auditor, Architekt | Ich, Tagesstart (Routing), Coach | agent-stop, route_findings.py |
| `.keel/work/coach/`, `briefing/` | Coach, Supervisor | Ich, Coach | agent-stop |
| `.keel/work/hinweise/` | Ich, über `/keel:hilfe` | Coach (prüft, übernimmt nicht) | – |
| `.keel/decisions/pending/` → `done/` | PO, Lead, Coach, Tagesstart; entschieden vom Supervisor oder Mensch | Supervisor, Briefing, Inbox | agent-stop (Supervisor), briefing_needed.py |
| `.keel/adr/` | Planer (Entwurf), Architekt (Entwurf), PO (delegiert), Supervisor, Ich | alle | Inbox, Briefing, due.py |
| `~/.keel-metrics/<projekt>-<hash>/` (System-ADR 0020, `bin/keel path runtime`) | Hooks | Coach, metrics.py, due.py, lage.py (Hilfe, Monitor) | tool-gate sperrt alle anderen Rollen |
