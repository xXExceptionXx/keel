# keel auf einen Blick

Sechs Sichten auf dasselbe System. Alle Diagramme sind Mermaid und rendern direkt auf GitHub; die Quelle ist diese Datei.

## 1. Rollen und Beziehungen

Wer entscheidet, wer taktet, wer prüft. Durchgezogen: Aufruf oder Auftrag. Gestrichelt: Bericht. Der Mensch spricht nur mit dem PO (heute noch mit dem Lead zusammengelegt) und liest Auditor und Coach.

```mermaid
flowchart TD
    ICH(["Ich<br/>Zielbild, Qualitätsmerkmale, Befugnisse, Backlog-Reihenfolge"])
    AUD["Auditor<br/>täglich Diff, wöchentlich Gesamtstand"]
    COACH["Coach<br/>Kennzahlen, Hypothesen, Umfeld"]
    LEAD["Lead (Haupt-Session)<br/>Taktgeber, aggregiert, urteilt nicht<br/><i>PO vorerst zusammengelegt</i>"]
    PLAN["Planer"]
    TEST["Tester"]
    DEV["Entwickler"]
    REV["Reviewer"]
    ARC["Architekt<br/><i>noch nicht als Rolle</i>"]

    ICH -->|Problemstellung, Abnahme, Entscheidungen| LEAD
    LEAD -->|Vorhaben: Abnahmetests| TEST
    LEAD -->|Vorhaben: Plan / Aufgabe: Neuschnitt| PLAN
    LEAD -->|Aufgabe| TEST
    LEAD -->|Aufgabe| DEV
    LEAD -->|Aufgabe| REV
    LEAD -.->|Vorlagen, Abnahmenachweis| ICH
    AUD -.->|Prüfbericht| ICH
    COACH -.->|Coach-Bericht, Vorlagen mit Hypothese| ICH
    PLAN -.-x ARC

    classDef human fill:#fff3cd,stroke:#b58900,color:#000
    classDef outside fill:#e8f4fd,stroke:#2b6cb0,color:#000
    classDef future fill:#f5f5f5,stroke:#999,color:#666,stroke-dasharray: 4 4
    class ICH human
    class AUD,COACH outside
    class ARC future
```

Auditor und Coach stehen außerhalb der Befehlskette. Sie werden nicht vom Lead aufgerufen, sondern über eigene Befehle (`/keel:audit`, `/keel:coach`), und sie ändern nichts außer ihrem Bericht.

## 2. Tagesrhythmus

Jeder Tag beginnt frisch aus Dateien. Zwischen Tagesabschluss und Tagesstart liegen Audit und die Runde des Menschen.

```mermaid
flowchart LR
    A["/keel:tagesabschluss<br/>Übergabenotiz aus Artefakten<br/>Belege geprüft, Suite grün<br/>Tag day-YYYY-MM-DD"]
    B["/keel:audit<br/>frischer Auditor<br/>Diff seit letztem Tag<br/>Prüfbericht"]
    C(["Ich, ~10 Minuten<br/>/keel:inbox<br/>Vorlagen, Abnahmen, Backlog"])
    D["/keel:tagesstart<br/>Basis-Branch, Startcheck<br/>Befunde routen<br/>Empfehlung"]
    E["/keel:vorhaben name<br/>Aufgabenzyklus<br/>auf feature/name"]
    R["/keel:reparatur<br/>fix/R-Datum"]

    A --> B --> C --> D --> E --> A
    D -. Startcheck rot .-> R -.-> D

    classDef human fill:#fff3cd,stroke:#b58900,color:#000
    class C human
```

## 3. Ein Vorhaben von der Problemstellung bis zur Integration

Zustände des Plans. Der Mensch setzt genau zwei davon: `problemstellung` am Anfang und `abgenommen` am Ende.

```mermaid
stateDiagram-v2
    [*] --> problemstellung: Mensch schreibt Plan-Datei
    problemstellung --> abnahmetests_bereit: Tester schreibt Abnahmetests (rot)
    abnahmetests_bereit --> geplant: Planer schneidet Aufgaben
    abnahmetests_bereit --> strukturaenderung: Planer braucht Strukturänderung
    strukturaenderung --> blockiert: Lead schreibt Vorlage
    geplant --> in_arbeit: Lead startet Aufgabenzyklus
    in_arbeit --> in_arbeit: je Aufgabe Tester, Entwickler, Reviewer, Commit
    in_arbeit --> blockiert: zweiter Neuschnitt derselben Aufgabe, Vorlage
    blockiert --> in_arbeit: Mensch entscheidet
    in_arbeit --> abnahme_bereit: Abnahmetests grün, Nachweis geschrieben
    in_arbeit --> abnahme_rot: Abnahmetests rot
    abnahme_bereit --> abgenommen: Mensch nimmt ab
    abgenommen --> integriert: Lead mergt in Basis, Abnahmetests werden Regression
    integriert --> [*]
```

## 4. Der Aufgabenzyklus mit seinen Rückläufen

Der Weg nach vorn ist kurz. Entscheidend sind die Rückläufe, und die sind feste Übergaben.

```mermaid
stateDiagram-v2
    [*] --> geplant: Planer
    geplant --> tests_bereit: Tester schreibt Aufgabentests
    tests_bereit --> fertig_gemeldet: Entwickler, Prüftor grün beim Beenden
    tests_bereit --> testeinspruch: Entwickler hält Test für falsch
    tests_bereit --> budget_erschoepft: Hook stoppt bei Aufrufen, Zeit oder Diff
    fertig_gemeldet --> review: Lead setzt Runde +1
    review --> fertig: Reviewer bestanden, Lead committet
    review --> nacharbeit: Befunde, Runde 1
    nacharbeit --> fertig_gemeldet: frischer Entwickler mit Befunden
    review --> neuschnitt: Befunde nach Runde 2
    testeinspruch --> neuschnitt
    budget_erschoepft --> neuschnitt
    neuschnitt --> geplant: Planer schneidet neu, tests leer
    neuschnitt --> ersetzt: Planer ersetzt durch kleinere Aufgaben
    neuschnitt --> verworfen: Planer verwirft
    fertig --> [*]
    ersetzt --> [*]
    verworfen --> [*]
```

## 5. Was die Hooks um eine Rolle herum tun

Am Beispiel des Entwicklers. Jede Prüfung ist deterministisch und unabhängig vom Modell; blockiert wird mit dem konkreten Mangel, nicht mit einer Bitte.

```mermaid
sequenceDiagram
    participant L as Lead
    participant G as agent-gate (PreToolUse Agent)
    participant S as agent-start (SubagentStart)
    participant D as Entwickler
    participant T as tool-gate (PreToolUse)
    participant E as agent-stop (SubagentStop)

    L->>G: Agent keel:entwickler, "Aufgabe: V1-T02"
    G->>G: Vordergrund? Rolle nicht schon aktiv?<br/>Aufgabe hat status tests-bereit, tests und dateien gefüllt?
    G-->>L: deny mit Grund (bei Verstoß)
    G->>S: Referenz V1-T02 geparkt
    S->>S: agent_id an V1-T02 gebunden, Zähler und Uhr auf 0
    loop jeder Werkzeugaufruf
        D->>T: Read, Edit, Bash …
        T->>T: Testdatei des Testers? Kennzahlen-Ordner?<br/>Aufrufe über Budget? Zeit über Budget?
        T-->>D: deny mit Grund (bei Verstoß)
    end
    D->>E: fertig, Abschlussnachricht
    E->>E: höchstens 3 Zeilen?<br/>status fertig-gemeldet mit nachweis?<br/>Prüftor grün? Diff unter Grenze?
    E-->>D: block: weiterarbeiten mit Grund
    E-->>L: Rückkehr mit 3 Zeilen
```

## 6. Lernschleife und Branches

Links die Lernschleife: Rohdaten entstehen nebenbei, niemand meldet Kennzahlen. Rechts das Branch-Modell: `main` fasst das System nie an, außer es ist die konfigurierte Basis.

```mermaid
flowchart LR
    subgraph Lernschleife
        H["Hooks<br/>events.jsonl, hooks.jsonl<br/>außerhalb des Repos"]
        AR["Artefakte<br/>Aufgaben, Reviews, Audits<br/>Entscheidungen, ADRs, Git-Log"]
        M["metrics.py<br/>Kennzahlen gegen Korridore"]
        CO["Coach<br/>Hypothesen prüfen<br/>Umfeld, Vorschläge"]
        V["Vorlagen mit Hypothese"]
        I(["Ich entscheide"])
        SA["System-ADR im Plugin<br/>Justierung umgesetzt"]
        H --> M
        AR --> M
        M --> CO --> V --> I --> SA
        SA -. nächster Lauf prüft Hypothese .-> CO
    end
    subgraph Branches
        MAIN[("main<br/>manueller Schritt des Menschen")]
        BASE[("Basis: develop / staging<br/>git.base_branch")]
        F["feature/name<br/>ein Commit je Aufgabe<br/>Trailer Keel-Task"]
        X["fix/R-Datum<br/>Reparatur"]
        BASE --> F -->|Merge nach Abnahme| BASE
        BASE --> X -->|Merge nach Review| BASE
        BASE -. Mensch .-> MAIN
    end
    classDef human fill:#fff3cd,stroke:#b58900,color:#000
    class I human
```

## 7. Wer schreibt was, wer liest was

| Artefakt | Schreibt | Liest | Prüft an der Grenze |
| --- | --- | --- | --- |
| `.keel/zielbild.md`, `qualitaetsmerkmale.md`, `befugnisse.md` | Ich | Lead, Planer, Auditor, Coach | – |
| `.keel/backlog.md` oder GitHub Issues | Ich (Reihenfolge), Tagesstart (Befunde), Auditor via Vorschlag | Lead, Auditor, Coach, nur über `backlog.py` | – |
| `.keel/work/plans/<name>.md` | Ich (Problemstellung), Tester (Abnahmetests), Planer (Aufgaben), Lead (Status) | alle Rollen des Vorhabens | agent-gate, agent-stop |
| `.keel/work/tasks/<ID>.md` | Planer, Tester, Entwickler, Lead (Status, Runden) | Tester, Entwickler, Reviewer, Auditor | agent-gate, agent-stop |
| `.keel/work/reviews/<ID>-r<n>.md` | Reviewer | Entwickler (Nacharbeit), Auditor, metrics.py | agent-stop |
| `.keel/work/acceptance/<name>.md` | Lead | Ich, Auditor | – |
| `.keel/work/handoff/<Datum>.md` | Lead (Tagesabschluss) | Tagesstart, Auditor | check_references.py |
| `.keel/work/audit/<Datum>.md` | Auditor | Ich, Tagesstart (Routing), Coach | agent-stop, route_findings.py |
| `.keel/work/coach/<Datum>.md` | Coach | Ich, nächster Coach | agent-stop |
| `.keel/decisions/pending/` | Lead, Coach, Tagesstart (aus Befunden) | Ich | Inbox |
| `.keel/adr/` | Planer (Entwurf), Ich, PO | alle | Inbox zeigt Proposed |
| `~/.keel-metrics/<projekt>/` | Hooks | Coach, metrics.py | tool-gate sperrt alle anderen Rollen |
