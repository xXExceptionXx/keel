# Agenten-Setup für autonome Softwareentwicklung

2026-09-19 · @Someone

## Zielbild

Ein schlankes, sequenzielles System, das Produktentwicklung entlang eines Zielbilds möglichst autonom durchführt.

## Zweck und Grundprinzipien

Das Setup soll mir erlauben, strategisch zu steuern: Ich entscheide über das Was, die Agenten lösen das Wie. Es ist auf wenige, entscheidende Eingriffe ausgelegt, nicht auf Geschwindigkeit.

- **Aufmerksamkeit ist der Engpass.** Nicht die Geschwindigkeit der Agenten. Ein System, das alle zehn Minuten eine Entscheidung verlangt, hat nichts abgenommen.
- **Sequenziell statt parallel.** Das spart Tokens, vermeidet Konflikte im Code und macht jede Übergabe nachvollziehbar. Parallel nur gezielt, etwa Tester und Entwickler auf derselben Aufgabe.
- **Zustand lebt in Dateien, nicht in Sessions.** Jede Rolle muss jederzeit frisch starten können. Faustregel: Tut ein Neustart weh, steckt zu viel Wissen im Kontext.
- **Spezialisierte Rollen mit wenig Kontext.** Jede Rolle sieht nur ihren Ausschnitt. Das reduziert Rauschen und Drift.
- **Übergaben sind feste Artefakte.** Keine freien Nachrichten zwischen Rollen, sonst entsteht stille Post.
- **Korrekturen gehen an die Maßstäbe.** Wenn ich eingreife, prüfe ich, ob eine Regel im Zielbild fehlt. Dann wird die Regel ergänzt, nicht nur der Einzelfall korrigiert.

## Hierarchie und Beziehungen

Ich spreche im Alltag mit dem Supervisor, im Morgen-Briefing, und schreibe Backlog-Einträge; ich lese die Berichte von Auditor und Coach. Alles darunter läuft über feste Übergaben. Stand 2026-09-22; das ursprüngliche Diagramm ohne Supervisor, Compliance-Rolle und Epic-Ebene ist durch `docs/system.md` ersetzt.

```mermaid
flowchart TD
    ICH["Ich<br/>Zielbild, Rangfolge, Befugnisse, Roadmap, Richtung"]
    SUP["Supervisor<br/>rechte Hand, entscheidet seine Stufe, Briefing"]
    COACH["System-Coach<br/>Lernschleife, bei Fälligkeit"]
    AUD["Auditor<br/>tägliche Prüfung, Wochenlauf"]
    LEAD["Lead<br/>/keel:start, /keel:stop, taktet"]
    PO["Product Owner<br/>Was und Warum, Abnahme"]
    ARC["Architekt<br/>Bewertung, Epic-Bewertung, Bestand, Drift"]
    PLAN["Planer<br/>schneidet Aufgaben"]
    TEST["Tester<br/>Tests vorab"]
    DEV["Entwickler<br/>eine kleine Aufgabe"]
    REV["Reviewer<br/>prüft pro Aufgabe"]
    COMP["Compliance<br/>Scan als Hook, Rolle bei Ermessen"]

    ICH <-->|Briefing| SUP
    ICH -->|Backlog-Eintrag| LEAD
    LEAD -->|Vorlage| SUP
    SUP -.->|richtungsweisend| ICH
    AUD -.->|Prüfbericht| ICH
    COACH -.->|Justierungsvorschläge| ICH
    LEAD --> PO
    LEAD --> ARC
    PO <-.->|max. 2 Runden| ARC
    LEAD --> PLAN
    LEAD -->|Abnahmetests, Aufgabentests| TEST
    LEAD --> DEV
    LEAD --> REV
    LEAD --> COMP
```

Gestrichelte Linien sind Rückläufe. Sie sind genauso feste Übergaben wie der Weg nach vorn, siehe Aufgabenzyklus.

Auditor und System-Coach stehen bewusst außerhalb der Befehlskette und berichten direkt an mich. Der Auditor prüft, ob das Produkt in die richtige Richtung läuft. Der Coach prüft, ob die Maschine gut läuft.

| Rolle | Ebene | Berichtet an | Läuft wann | Lebensdauer |
| --- | --- | --- | --- | --- |
| Ich | Strategie | – | täglich, feste Zeitfenster | – |
| Supervisor | Richtung innerhalb der Roadmap | Ich | bei jeder Vorlage, morgens im Briefing | kurz, pro Anlass; Briefing als Session |
| System-Coach | System | Ich | bei Fälligkeit: Tage und Rollenläufe über den Schwellen | kurz, pro Lauf |
| Auditor | Kontrolle | Ich | einmal täglich | kurz, pro Prüfung |
| Product Owner | Produkt | Supervisor, Ich | Problemstellung, Epic-Skizze, Abstimmung, Klärung, Abnahme; vom Lead aufgerufen | kurz, pro Anlass |
| Architekt | System | PO | bei Bedarf, wöchentlich | kurz, pro Anlass |
| Lead | Ablauf | PO | durchgehend als Taktgeber | bis zum nächsten Zwischenabschluss |
| Planer | Feature | Lead | pro Vorhaben | kurz, pro Vorhaben |
| Tester | Vorhaben und Aufgabe | Lead | pro Vorhaben (Abnahmetests), pro Aufgabe (Aufgabentests) | kurz, pro Anlass |
| Entwickler | Aufgabe | Lead | pro Aufgabe | kurz, pro Aufgabe |
| Reviewer | Aufgabe | Lead | pro Aufgabe | kurz, pro Aufgabe |
| Compliance | Aufgabe | Lead | Scan beim Beenden jedes Entwicklers, Rolle nur bei Ermessensbefunden | kurz, pro Aufgabe |

Autorität und Ablaufsteuerung sind getrennt: Der PO steht über dem Lead, weil er über das Was entscheidet. Der Lead ist aber der Taktgeber, der ihn bei Anlass aufruft. Der Lead ist damit die einzige langlebige Rolle.

Der Lead urteilt nicht, er aggregiert: Eine Aufgabe ist fertig, wenn alle Tore grün sind (Tests, Review, Compliance, Prüftor). Der Lead prüft die Vollständigkeit der Artefakte, nicht ihren Inhalt. Sonst schleicht sich Urteil in die einzige langlebige Rolle.

## Rollen im Detail

Jede Rolle hat einen klaren Auftrag und eine klare Grenze. Die Grenze ist genauso wichtig wie der Auftrag: Sie verhindert, dass eine Rolle in die Ebene einer anderen rutscht.

### Ich

- **Auftrag:** Zielbild, Qualitätsmerkmale und Befugnisse festlegen. Backlog priorisieren: Welche Probleme als Nächstes dran sind, entscheide ich, nicht der PO. Vorlagen entscheiden. Delegierte ADRs gebündelt durchsehen.
- **Input:** Prüfbericht, Entscheidungs-Inbox, Wochenbericht des Auditors.
- **Grenze:** Keine Aufgaben, kein Code. Ich greife in Maßstäbe ein, nicht in Einzelfälle.

### Auditor

- **Auftrag:** Einmal täglich prüfen, ob die Richtung stimmt. Passen die Änderungen zum Zielbild? Blieben delegierte Entscheidungen im Rahmen? Wurden ADRs oder die Architektur verletzt? Stimmt die Übergabenotiz mit dem Code überein? Stimmt der Plan mit dem Code überein, sind als erledigt markierte Aufgaben wirklich gelandet?
- **Wochenlauf:** Einmal pro Woche prüft der Auditor nicht den Diff, sondern den Gesamtstand gegen das Zielbild. Viele einzeln unauffällige Tage können zusammen in die falsche Richtung laufen. Der Tageslauf sieht das nicht, weil er nur die Differenz kennt. Der Wochenlauf ist das Gegenstück zur Wochenrunde des Architekten: dort technische Drift, hier Produktdrift.
- **Input:** Tageslauf: Diff seit dem letzten Tages-Tag, neue und geänderte ADRs, Zielbild, Akzeptanzkriterien, Architekturdokument, Plan-Datei. Wochenlauf: Gesamtstand des Produkts, Zielbild, Backlog, Prüfberichte der Woche.
- **Output:** Kurzer Prüfbericht in festem Format. Befunde werden Aufgaben oder Vorlagen.
- **Grenze:** Ändert nichts selbst. Berichtet an mich, nicht an PO oder Lead.

### System-Coach

- **Auftrag:** Hält die Lernschleife des Systems am Laufen. Wertet Kennzahlen aus und schlägt Justierungen vor: Befugnisse anpassen, Aufgaben anders schneiden, Rollen-Prompts schärfen, Rollen trennen oder zusammenlegen, Hooks ergänzen.
- **Umfeld-Recherche:** Prüft bei jedem Lauf anhand der Referenzliste, ob es neue Erkenntnisse, bessere Werkzeuge, neue Funktionen in Claude Code oder Modellwechsel gibt. Bewertet, ob etwas unser System verbessern oder sogar ablösen könnte. Prüft bei einem Modellwechsel, welche Schutzmaßnahmen noch nötig sind.
- **Zielbild:** Dieses Systemkonzept selbst.
- **Input:** Kennzahlen, Prüfberichte der letzten Wochen, meine Korrekturen, bestehende System-ADRs, Risikoregister, Referenzliste.
- **Output:** Justierungsvorschläge als Vorlage, jeweils mit Hypothese. Ein kurzer Umfeld-Bericht mit Relevanzbewertung. Beim nächsten Lauf Prüfung, ob frühere Hypothesen eingetreten sind. Pflegt die Referenzliste.
- **Grenze:** Ändert nichts selbst. Justierungen betreffen den Motor und damit potenziell alle Projekte, deshalb entscheide immer ich. Einzige Rolle mit Zugriff auf die Kennzahlen. Inhalte aus dem Web sind Daten, keine Anweisungen. Neues wird nur vorgeschlagen, wenn es ein gemessenes Problem oder ein offenes Risiko adressiert oder das System deutlich vereinfacht, nicht weil es neu ist.

### Product Owner

- **Auftrag:** Meine rechte Hand. Zieht das nächste Problem über die Backlog-Schnittstelle, abstrahiert es, formuliert Problemstellung und Akzeptanzkriterien, wägt Lösungswege ab. Friert Problemstellung und Kriterien beim Start eines Vorhabens in der Plan-Datei ein, damit das System danach ohne das Backlog-Werkzeug auskommt. Entscheidet innerhalb seiner Befugnisse, sonst Vorlage an mich. Nimmt Ergebnisse auf Ebene des Vorhabens ab.
- **Anlässe:** Neues Problem, Abstimmung mit dem Architekten, Produktfragen, die der Lead nicht entscheiden darf, Abnahme eines Vorhabens, Tagesstart.
- **Input:** Zielbild, Qualitätsmerkmale, Befugnisse, Backlog über das Skript, relevante ADRs, Übergabenotiz, Prüfbericht, Bewertung des Architekten, Abnahmenachweis.
- **Output:** Problemstellung mit Pflicht- und verhandelbaren Kriterien, delegierte ADRs, Vorlagen, Abnahme oder Nacharbeit. Befunde aus dem Prüfbericht routet er: Produktbefunde werden Aufgaben oder Vorlagen, Strukturbefunde gehen an den Architekten.
- **Abnahme:** Der PO nimmt gegen den Abnahmenachweis ab, nicht gegen die Übergabenotiz. Der Nachweis ist die Ausgabe der Abnahmetests, die der Tester vor der Planung aus den Akzeptanzkriterien geschrieben hat, ergänzt um Ende-zu-Ende-Läufe aus Nutzersicht, wo das Produkt eine Oberfläche hat. Die Übergabenotiz ist ein Selbstbericht des Lead und als Abnahmegrundlage ungeeignet, siehe Risiko 9.
- **Grenze:** Verantwortet das Was und Warum. Denkt nicht über Umsetzung oder Systemstruktur nach. Prüft keine einzelnen Entwickleraufgaben, das ist Sache des Reviewers. Kein Gedächtnis in der Session: Alles Nötige liegt in Dateien, er beendet sich nach jedem Anlass.

### Architekt

- **Auftrag:** Hält die Gesamtstruktur von Backend und Frontend. Bewertet, ob ein Vorhaben ins System passt und was es kostet. Schützt gegen technischen Drift: übersetzt Muster in Prüfregeln, bestimmt Referenzbeispiele und sucht in der Wochenrunde gezielt nach Drift, die durch die Regeln gerutscht ist. Pflegt die Tool-Skills und die zugehörigen Skripte.
- **Input:** Problemstellung des PO, Anfragen des Planers, Verstöße gegen Architekturregeln, Werkzeugprobleme aus den Übergabenotizen.
- **Output:** Architekturdokument, API-Vertrag, Datenmodell, Prüfregeln, Referenzbeispiele, Tool-Skills und Skripte, ADR-Entwürfe für strukturelle Änderungen.
- **Grenze:** Kein Veto über das Produkt, aber die Pflicht, Kosten ehrlich zu benennen. Läuft nur bei Bedarf und wöchentlich als Aufräumrunde.
- **Wahrscheinlichste Trennlinie:** Der Architekt trägt zwei Berufe: Systemstruktur, Prüfregeln und Referenzbeispiele auf der einen Seite, Tool-Skills, Skripte und Umgebung auf der anderen. Letzteres ist Plattformarbeit, keine Architektur. Wird eine Rolle als Erste überladen, dann diese, und die Trennung verläuft genau hier: Architekt und Plattform.

### Lead

- **Auftrag:** Taktgeber des Systems. Orchestriert den Ablauf vom Plan bis zum Abschluss und ruft die anderen Rollen bei Anlass auf, auch den PO. Führt auch die Abstimmungsrunden zwischen PO und Architekt als sequenzielle Aufrufe mit Dateiübergabe aus, damit die Runden zählbar bleiben. Stellt fest, ob eine Aufgabe fertig ist: alle Tore grün. Schreibt Zwischenübergaben nach Arbeitseinheiten und die Übergabenotiz zum Tagesende, inklusive Werkzeugproblemen.
- **Input:** Problemstellung des PO, knappe Statusmeldungen der anderen Rollen.
- **Output:** Zwischenübergaben, Übergabenotiz, Fortschrittslog.
- **Grenze:** Implementiert nicht selbst und trifft keine Produktentscheidungen. Liest keine vollständigen Berichte, siehe Kontextschutz. Urteilt nicht über Inhalte, sondern prüft Vollständigkeit. Improvisiert nicht bei kaputtem Zustand: Ein roter Startcheck oder ein roter Hauptzweig erzeugt deterministisch eine Reparaturaufgabe mit Vorrang, siehe Integration und Zustand.

### Planer

- **Auftrag:** Schneidet ein Vorhaben in kleine, in sich geschlossene Aufgaben mit Fertig-Kriterien. Gibt jeder Aufgabe eine Aufgaben-ID, den Verweis auf das passende Referenzbeispiel und die Liste der relevanten Dateien mit. Entwirft ADRs, wenn der Plan eine echte Entscheidung enthält. Nimmt Rückläufer an: Testeinsprüche, erschöpfte Budgets und Aufgaben nach der zweiten Review-Runde werden neu geschnitten, nicht durchgedrückt.
- **Input:** Problemstellung, Abnahmetests, Architekturdokument, Codebasis.
- **Output:** Plan-Datei mit Aufgabenliste.
- **Grenze:** Plant innerhalb der bestehenden Architektur. Braucht es eine Strukturänderung, geht die Frage an den Architekten. Darf viel lesen, weil er kurzlebig ist: Wer ohne Blick in den Code schneidet, schneidet falsch und benennt die falschen Dateien. Dann sucht jeder Entwickler von vorn.

### Tester

- **Auftrag:** Zwei Anlässe, gleiche Rolle, anderer Input.
  - **Abnahmetests pro Vorhaben:** Aus den Akzeptanzkriterien des PO, bevor der Planer schneidet. Sie sind das Sicherheitsnetz gegen „alle Aufgaben grün, Problem trotzdem nicht gelöst“ und liefern den Abnahmenachweis für den PO. Wo das Produkt eine Oberfläche hat, gehören Ende-zu-Ende-Läufe aus Nutzersicht dazu, etwa per Browser-Automatisierung.
  - **Aufgabentests pro Aufgabe:** Aus den Fertig-Kriterien, bevor der Entwickler beginnt.
- **Input:** Akzeptanzkriterien bzw. Aufgabe mit Fertig-Kriterien, Referenzbeispiel für Tests.
- **Output:** Tests im Repo, kurze Statusmeldung.
- **Grenze:** Spricht sich nicht mit dem Entwickler ab. Genau das macht die Tests unabhängig. Bei einem Testeinspruch des Entwicklers bekommt er die Aufgabe über den Planer zurück, nie direkt.

### Entwickler

- **Auftrag:** Setzt genau eine kleine Aufgabe um.
- **Input:** Die Aufgabe, relevante Dateien, die Tests.
- **Grenze:** Frischer Kontext pro Aufgabe. Kein Blick auf das Gesamtbild, keine eigenen Architekturentscheidungen. Darf die Tests des Testers nicht ändern. Meldet „fertig“ nur mit Nachweis, etwa der Testausgabe.
- **Testeinspruch:** Hält er einen Test für falsch, baut er nicht drumherum. Er meldet „Test widerspricht Kriterium X“ mit Begründung als festen Status. Die Aufgabe geht an den Planer zurück, der mit dem Tester klärt. Ohne diesen Ausweg bleiben nur zwei schlechte Wege: stecken bleiben oder den Test formal erfüllen.
- **Budget:** Jede Aufgabe hat eine Obergrenze für Werkzeugaufrufe, Laufzeit und Diff-Größe, siehe Aufgabenzyklus. Ist sie erreicht, meldet er den Stand und beendet sich. Ein festgefahrener Entwickler ist teurer als ein Neuschnitt, und ohne Grenze drängt er zum Abschluss.

### Reviewer

- **Auftrag:** Prüft, ob die Aufgabe richtig gelöst ist, und prüft den Nachweis des Entwicklers.
- **Input:** Nur Diff, Aufgabe, Fertig-Kriterien und die ursprünglichen Akzeptanzkriterien des PO. Nicht die Gedankengänge des Entwicklers. Der Diff enthält ausdrücklich auch die Tests des Testers: Tests sind Code und werden sonst von niemandem geprüft. Ab Runde zwei zusätzlich die Befunde der Vorrunde und das Delta der Nacharbeit als eigenen Diff: Ein Fix ist Code wie jeder andere und wird so gründlich geprüft wie die erste Umsetzung.
- **Output:** Befunde in festem Format: Schweregrad, Herkunft, Fundstelle, Beschreibung, dazu die Zahl je Schweregrad. Das Format dient dem Entwickler und ist zugleich maschinell auswertbar: Ob die Aufgabe besteht, rechnet ein Hook gegen eine Schwelle aus der Konfiguration.
- **Grenze:** Nur Lesezugriff. Widerspricht ein PR einem angenommenen ADR, ist das kein Kommentar, sondern erzwingt ein neues ADR. Neue Befunde in Code, den die Nacharbeit nicht angefasst hat, sind nur mit hohem Schweregrad erlaubt, alles andere wird Anmerkung; neue Befunde im Delta der Nacharbeit zählen voll. Anmerkungen blockieren nicht, landen aber in der Pflegeliste, die der Architekt wöchentlich sichtet.

### Compliance

- **Auftrag:** Deterministische Prüfungen als Hook: Linter, Secret-Scan, Lizenzen, Abhängigkeits-Scan auf bekannte Lücken (z. B. `npm audit`, `composer audit`) und Lockfile-Integrität. Als Agent nur für Ermessensfragen, vor allem Datenschutz nach DSGVO bei personenbezogenen Daten.
- **Auslöser für den Agenten:** Deterministisch, nicht nach Gefühl. „Nur bei Ermessensfragen“ heißt in der Praxis nie, weil niemand entscheidet, dass eine vorliegt. Ein Hook startet den Agenten, wenn der Diff eines der Muster trifft: neue Tabelle oder Migration, neue Felder mit PII-Mustern (Name, E-Mail, Adresse, Geburtsdatum, IP), neuer externer Aufruf, neue Abhängigkeit, Änderungen an Logging oder Auth. Die Musterliste ist Konvention als Code und wird vom Architekten gepflegt.
- **Grenze:** Blockiert den Abschluss, entscheidet aber nicht über Produkt oder Architektur.

### Zusammenlegen zum Start

Anfangs können Rollen zusammengelegt werden, etwa Tester und Reviewer oder PO und Lead. Getrennt wird erst, wenn eine Rolle spürbar überladen ist. Die erste Trennung wird voraussichtlich Architekt und Plattform sein, siehe Architekt.

## Aufgabenzyklus und Rücklauf

Der Weg nach vorn ist einfach: Tester, Entwickler, Reviewer, Compliance, Lead. Entscheidend ist, was bei Befunden, falschen Tests und festgefahrenen Aufgaben passiert. Rückläufe sind feste Übergaben, keine Improvisation des Lead.

```mermaid
stateDiagram-v2
    [*] --> Tests: Tester schreibt Aufgabentests
    Tests --> Umsetzung: frischer Entwickler
    Umsetzung --> Review: fertig mit Nachweis
    Umsetzung --> Neuschnitt: Testeinspruch
    Umsetzung --> Neuschnitt: Budget erschöpft
    Review --> Compliance: unter der Schwelle
    Review --> Umsetzung: über der Schwelle, Befunde sinken
    Review --> Vorlage: Befunde sinken nicht
    Vorlage --> Neuschnitt: Supervisor
    Compliance --> Fertig: Tore grün
    Compliance --> Umsetzung: Verstoß
    Neuschnitt --> Tests: Planer hat neu geschnitten
    Fertig --> [*]
```

Regeln:

- **Aufgaben-ID.** Jede Aufgabe bekommt vom Planer eine ID, z. B. `V12-T03` für Vorhaben 12, Aufgabe 3. Sie steht im Plan, im Branch-Namen, als Commit-Trailer, in der Review-Datei und in den Hook-Logs. Sie ist der Schlüssel, über den Kennzahlen aus Artefakten abgeleitet werden. Ohne sie ist „Tokens pro Aufgabe“ nicht berechenbar. Die Vorhaben-Nummer ist systemintern und nicht die Nummer des Backlog-Elements; die Plan-Datei verweist im Frontmatter auf das Element, z. B. `backlog: github#12`. So überleben alle Verweise einen Anbieterwechsel.
- **Nacharbeit immer mit frischem Entwickler.** Er bekommt die Aufgabe, den bisherigen Diff und die Befunde des Reviewers. Nicht den Kontext des Vorgängers: Der hat die Aufgabe schon einmal falsch verstanden.
- **Review-Runden, solange die Befunde sinken.** Jede Nacharbeit wird erneut reviewt, denn Fixes bauen selbst Fehler ein. Eine weitere Runde gibt es nur, wenn (blockierend, wichtig) gegenüber der Vorrunde sinkt, höchstens vier. Sinken die Befunde nicht, ist die Aufgabe falsch geschnitten oder falsch spezifiziert, und eine weitere Runde behebt weder das eine noch das andere: Der Supervisor gibt sie in den Neuschnitt oder eskaliert. Siehe System-ADR 0018. Ursprünglich galten höchstens zwei Runden; das hat Fehler aus der zweiten Nacharbeit ungeprüft durchgelassen.
- **Testeinspruch geht über den Planer.** Der Entwickler meldet den Widerspruch mit Begründung, der Planer klärt mit dem Tester, ob Test oder Kriterium falsch ist. Ist das Kriterium unklar, geht die Frage zum PO. Tester und Entwickler sprechen nie direkt.
- **Budget pro Aufgabe.** Startwerte: 60 Werkzeugaufrufe, 30 Minuten, 300 Diff-Zeilen ohne Tests. Erreicht der Entwickler die Aufruf- oder Diff-Grenze, schreibt er den Stand in die Aufgaben-Datei und beendet sich. Diese Grenzen werden per Hook durchgesetzt, nicht per Bitte. Die Minuten sind seit System-ADR 0021 nur eine Meldeschwelle: Ein Lauf darüber meldet einmal `budget_slow` und wird nicht gestoppt. Die Werte werden vom Coach kalibriert. Regelmäßige Überschreitungen heißen: Der Planer schneidet zu groß.
- **Verworfene Ansätze schreibt, wer sie verworfen hat.** Entwickler und Planer tragen Irrwege direkt in die Datei ein. Der Lead kennt sie nicht, weil er keine vollständigen Berichte liest.

## Integration und Zustand

Sequenzielle Arbeit heißt nicht, dass Integration von selbst passiert. Der Zustand des Hauptzweigs und der Umgebung braucht einen Besitzer und feste Regeln.

- **Ein Branch pro Vorhaben, ein Commit pro Aufgabe.** Aufgaben landen als Commits mit Aufgaben-ID und Trailer `Keel-Task: <ID>` auf `feature/<name>`, abgezweigt vom konfigurierten Basis-Branch (`git.base_branch`, etwa `develop` oder `staging`). Nach der Abnahme durch den PO integriert der Lead in die Basis: Merge, Abnahmetests in die Regressionssuite, Branch löschen. Der Weg von der Basis nach `main` bleibt ein manueller Schritt des Menschen. Reparaturen laufen auf `fix/<ID>` und werden nach dem Review sofort gemergt. Siehe System-ADRs 0003 und 0004.
- **Aufgaben-Tests pro Aufgabe, gesamte Suite pro Vorhaben.** Das Prüftor jeder Aufgabe läuft die Aufgabentests und einen schnellen Stichproben-Modus. Vor der Abnahme eines Vorhabens läuft die gesamte Suite plus Abnahmetests. Vor dem täglichen Audit läuft die gesamte Suite auf dem Hauptzweig, damit der Auditor einen bekannten Zustand prüft.
- **Roter Startcheck oder roter Hauptzweig erzeugt eine Reparaturaufgabe.** Deterministisch, mit Vorrang vor allem anderen, mit eigener ID und eigenem Budget. Der Lead spawnt dafür einen Entwickler mit der Aufgabe „Startcheck grün machen“ und den Logs als Input. Der Lead repariert nie selbst. Ist die Reparatur nach einem Budget nicht geschafft, wird sie zur Vorlage.
- **Tagesabschluss nur an Aufgabengrenzen.** Der Lead beendet den Tag nicht mitten in einer Aufgabe. Entweder die Aufgabe wird fertig oder sie wird zurückgesetzt und morgen frisch begonnen. Halbfertige Branches sind der häufigste Grund für kaputten Zustand zwischen Sessions.
- **Kein Produktionszugang, keine destruktiven Befehle.** Agenten arbeiten nur gegen lokale oder isolierte Umgebungen. Force-Push, Branch-Löschung, `rm -rf` außerhalb des Arbeitsverzeichnisses, Datenbank-Drops und Produktions-Credentials werden per Berechtigungsregel gesperrt, bevor der erste autonome Lauf startet. Das ist Punkt 1 der Einführung, nicht ein offener Punkt im Risikoregister.

## Abstimmung zwischen PO und Architekt

Produkt und Architektur sind immer ein Kompromiss. Deshalb ist die Abstimmung ein fester Schritt, bevor der Lead übernimmt. Manchmal fügt sich das Produkt der Architektur, manchmal umgekehrt.

```mermaid
sequenceDiagram
    participant PO as Product Owner
    participant ARC as Architekt
    participant ICH as Ich
    PO->>ARC: Problemstellung, Pflicht- und verhandelbare Kriterien
    ARC->>PO: Bewertung in 3 Stufen + Kosten, ggf. abgespeckte Variante
    PO->>ARC: Rückfrage oder Kompromissvorschlag (Runde 2)
    ARC->>PO: Finale Bewertung
    alt Einigung im Rahmen der Befugnisse
        PO->>PO: Entscheidet, ADR mit Status delegiert
    else Keine Einigung oder schwer umkehrbar
        PO->>ICH: Vorlage mit beiden Positionen
    end
```

Die Bewertung des Architekten kennt drei Stufen:

1. **Passt so** ins bestehende System.
2. **Passt mit kleiner Anpassung.**
3. **Braucht eine strukturelle Änderung.** Liegen Pflichtkriterien hier, schlägt der Architekt zusätzlich eine abgespeckte Produktvariante vor, die in Stufe 1 oder 2 fällt.

Regeln:

- **Höchstens zwei Runden.** Danach geht eine Vorlage mit beiden Positionen an mich.
- **Der PO entscheidet den Kompromiss.** Die Abwägung ist eine Produktentscheidung auf Basis der sichtbar gemachten Kosten.
- **Tiebreaker ist die Rangfolge der Qualitätsmerkmale.** Ohne Rangfolge wird jeder Konflikt zur Vorlage.
- **Beide Ausgänge werden als ADR dokumentiert.** Setzt sich das Produkt durch: bewusste Abweichung, entstehende technische Schulden und die Bedingung für ihren Abbau. Setzt sich die Architektur durch: warum das Feature eingeschränkt ist, damit die Frage nicht erneut gestellt wird.

## Entscheidungsbefugnisse und Eskalation

Maßstab für die Befugnisse ist die Umkehrbarkeit einer Entscheidung. Leicht umkehrbares entscheidet der PO selbst, schwer umkehrbares landet bei mir.

| Der PO entscheidet selbst | Vorlage an mich |
| --- | --- |
| Leicht rückgängig zu machen | Schwer umkehrbar |
| Keine Auswirkung auf Nutzer oder Kosten | Datenmodell, Architekturgrenzen, API-Vertrag |
| Innerhalb von Zielbild und Qualitätsmerkmalen | Neue externe Abhängigkeit |
| Dokumentiert als ADR mit Status *Accepted (delegiert)* | Kosten, personenbezogene Daten |
|  | Widerspruch zu einem angenommenen ADR |
|  | Keine Einigung zwischen PO und Architekt |

### Entscheidungs-Inbox

- Vorlagen landen in `decisions/pending/` und unterbrechen mich nicht.
- Ich arbeite sie zu festen Zeiten ab, morgens zusammen mit dem Prüfbericht.
- Ein offenes Thema blockiert das System nicht. Der PO parkt es und zieht andere Arbeit vor.
- Delegierte ADRs sehe ich gebündelt durch, etwa einmal pro Woche, und kann jede kippen.

### Format einer Vorlage

Eine Vorlage muss in einer Minute entscheidbar sein. Muss ich dafür Code lesen, hat der PO seine Arbeit nicht gemacht.

```markdown
# Vorlage: <Titel>

**Problem:** <zwei Sätze>

**Optionen:**
1. <Option A> – Folgen: …
2. <Option B> – Folgen: …

**Empfehlung:** <Option> – weil …

**Warum ich nicht selbst entscheide:** <Kriterium aus der Befugnistabelle>
```

### Kalibrierung

- **Zu viele Vorlagen:** Befugnisse zu eng oder Zielbild und Qualitätsmerkmale zu unscharf.
- **Auditor findet Fehlentscheidungen:** Spielraum zu weit.
- **Start:** Enger Spielraum, viele Vorlagen. Befugnisse schrittweise erweitern, wenn die Entscheidungen des PO zu meinen passen.

## Dokumentation

Alle Dokumentation liegt als Markdown im Repo. So ist sie mit dem Code versioniert, jeder Agent kann sie ohne Connector lesen, und das Warum lässt sich über `git blame` bis zur Entscheidung zurückverfolgen.

| Artefakt | Zweck | Pflegt | Liest | Lebensdauer |
| --- | --- | --- | --- | --- |
| Zielbild | Vision, Zielgruppen, was das Produkt nicht sein soll | Ich | PO, Auditor | dauerhaft |
| Qualitätsmerkmale | Priorisierte Kriterien, Tiebreaker bei Konflikten | Ich | PO, Architekt, Auditor | dauerhaft |
| Befugnisse | Was der PO selbst entscheiden darf | Ich | PO, Auditor | dauerhaft |
| Backlog | Priorisierte Probleme, aus denen der PO das nächste Vorhaben zieht. Hinter einer Schnittstelle, Anbieter austauschbar | Ich (Reihenfolge), PO und Auditor (Vorschläge) | PO, Auditor, Coach, nur über das Skript | dauerhaft, im Werkzeug des Anbieters |
| Backlog-Konfiguration | Welcher Anbieter, welches Projekt, Abbildung der Zustände | Architekt | Backlog-Skript | dauerhaft, als Projekt-ADR |
| Architekturdokument | Komponenten, Grenzen, C4-Diagramm | Architekt | Planer, Auditor | dauerhaft |
| API-Vertrag | Schnittstelle Backend–Frontend, z. B. OpenAPI | Architekt | Planer, Entwickler | dauerhaft |
| ADRs | Warum etwas so gebaut wurde, inkl. Umkehrungen | Planer, Architekt, PO | alle | dauerhaft |
| System-ADRs | Justierungen am System, jeweils mit Hypothese | System-Coach, Ich | Coach, Ich | dauerhaft, im Plugin-Repo |
| Risikoregister | Bekannte Fehlerquellen und ihre Abdeckung | System-Coach | Coach, Ich | dauerhaft, im Plugin-Repo |
| Referenzliste | Quellen für die Umfeld-Recherche | System-Coach | Coach | dauerhaft, im Plugin-Repo |
| Verworfene Ansätze | Irrwege, damit sie nicht wiederholt werden | Lead | Planer, PO | dauerhaft |
| Plan-Datei | Aufgaben eines Vorhabens mit ID, Fertig-Kriterien, relevanten Dateien. Frontmatter mit Verweis auf das Backlog-Element und eingefrorener Problemstellung | Planer, PO (Frontmatter) | Lead, Tester, Entwickler | pro Vorhaben |
| Aufgaben-Datei | Status, Nachweis, Befunde, Budgetstand einer Aufgabe | Entwickler, Reviewer, Hooks | Lead, Planer, Auditor | pro Aufgabe |
| Abnahmenachweis | Ausgabe der Abnahmetests eines Vorhabens | Tester, Skript | PO | pro Vorhaben |
| Fortschrittslog | Aktueller Stand, darf veralten | Lead | PO | flüchtig |
| Übergabenotiz | Tagesabschluss für den nächsten Start | Lead | Auditor, PO | ein Tag |
| Prüfbericht | Ergebnis des täglichen Audits | Auditor | Ich, PO, Coach | ein Tag |
| Wochenbericht | Ergebnis des wöchentlichen Audits gegen den Gesamtstand | Auditor | Ich, PO, Coach | eine Woche |
| Vorlagen | Entscheidungen, die ich treffen muss | PO, Coach | Ich | bis entschieden |
| Kennzahlen | Rohdaten für die Lernschleife, außerhalb des Repos | Hooks, Skripte | Coach, Ich | fortlaufend |

### ADRs

- Format nach MADR oder Nygard, eine Datei pro Entscheidung, fortlaufend nummeriert.
- Status: *Proposed* → *Accepted* oder *Accepted (delegiert)* → später ggf. *Superseded by 00XX*.
- Eine Umkehrung ändert nie das alte ADR. Es entsteht ein neues mit *Supersedes 00XX*, das alte bleibt als Historie erhalten.
- Die `CLAUDE.md` enthält nur einen kurzen Index der aktiven ADRs.
- Zum Lesen im Browser kann `log4brains` den ADR-Ordner als durchsuchbare Seite rendern.

### Übergaben mit Schema

Jede Übergabe-Datei (Plan, Aufgaben-Datei, Review, Übergabenotiz, Prüfbericht, Vorlage) beginnt mit einem YAML-Frontmatter mit Pflichtfeldern, z. B. Aufgaben-ID, Status, Rolle, Datum. Ein Hook prüft das Frontmatter an der Grenze: Fehlt ein Pflichtfeld oder hat der Status einen unbekannten Wert, gilt die Übergabe als nicht erfolgt und die nächste Rolle startet nicht. Markdown bleibt, weil Menschen die Dateien lesen. JSON braucht es dafür nicht, das Frontmatter ist maschinell prüfbar genug. Der Fließtext darunter ist für Menschen und die nächste Rolle, die Kennzahlen kommen aus dem Frontmatter.

### Dateistruktur

Alle Projektdaten des Systems liegen gesammelt in einem Namensraum-Ordner, getrennt von der eigentlichen Codebasis. Extrahieren heißt: einen Ordner verschieben.

```
CLAUDE.md                  bestehend, bekommt nur: @.keel/CLAUDE.md
.keel/
  CLAUDE.md                Zielbild-Kurzfassung, Index aktiver ADRs
  zielbild.md
  qualitaetsmerkmale.md
  befugnisse.md
  config.yaml              Backlog-Anbieter und Zustandsabbildung
  backlog.md               nur beim Markdown-Adapter, sonst leer
  architektur.md
  api/openapi.yaml
  adr/0001-….md
  verworfene-ansaetze.md
  work/
    plans/<vorhaben>.md
    tasks/<aufgaben-id>.md   Status, Nachweis, Befunde, Budget
    acceptance/<vorhaben>.md Abnahmenachweis
    progress.md
    handoff/<datum>.md
    audit/<datum>.md
    audit/week-<datum>.md
  decisions/
    pending/
    done/
  skills/                  projektspezifische Skills, per Symlink aus .claude/skills/
.claude/
  settings.json            Plugin-Eintrag und Deny-Regeln, siehe Installation
  skills -> ../.keel/skills
```

## Tagesrhythmus

Das gesamte System startet jeden Tag frisch. Drift kann so höchstens über einen Tag entstehen, weil der Plan morgens wieder aus den Dokumenten geladen wird.

```mermaid
flowchart LR
    A["Tagesabschluss<br/>Übergabenotiz + Git-Tag"] --> B["Audit<br/>frischer Auditor"]
    B --> C["Ich<br/>~10 Min. Bericht + Inbox"]
    C --> D["PO-Start<br/>liest nur Kurzfassungen"]
    D --> E["Arbeitstag<br/>sequenziell"]
    E --> A
```

1. **Tagesabschluss:** Nur an einer Aufgabengrenze. Der Lead schreibt die Übergabenotiz: erledigt, offen, getroffene Entscheidungen, Probleme. Die gesamte Testsuite läuft auf dem Hauptzweig. Dazu ein Git-Tag, z. B. `day-2026-09-19`, der den Prüfumfang für morgen abgrenzt.
2. **Audit:** Ein frischer Auditor lädt den Diff seit dem letzten Tag und die Maßstäbe. Er darf viel lesen, weil er danach beendet wird. Übrig bleibt nur sein Bericht. Einmal pro Woche läuft zusätzlich der Wochenlauf gegen den Gesamtstand.
3. **Meine Runde:** Etwa zehn Minuten für Prüfbericht und Entscheidungs-Inbox, zwei bis drei Entscheidungen. Einmal pro Woche dazu der Wochenbericht und das Backlog.
4. **Startcheck:** Ein Skript fährt die Umgebung hoch und führt den Basis-Test aus. Rot erzeugt eine Reparaturaufgabe mit Vorrang, siehe Integration und Zustand.
5. **PO-Start:** Der PO liest nur Zielbild, Backlog, Übergabenotiz und Prüfbericht. Wenige Seiten statt eines ganzen Tages Verlauf.

**Regel: Wer viel liest, schreibt wenig.** So kommt der Kontext des Vortags nicht durch die Hintertür zurück.

### Format des Prüfberichts

```markdown
# Prüfbericht <Datum>

**Gesamt:** passt | Abweichungen

**Abweichungen:**
- <Befund> – Fundstelle – wird Aufgabe | wird Vorlage

**Delegierte Entscheidungen zur Durchsicht:**
- ADR-00XX <Titel>

**Übergabenotiz vs. Code:** stimmt | Abweichung: …

**Plan vs. Code:** stimmt | Abweichung: …
```

Das feste Format ist wichtig. Ein Freitext-Bericht wächst mit der Zeit und bringt den Kontext zurück.

## Kontextschutz für den Lead

Der Lead ist die einzige langlebige Rolle und damit am anfälligsten für Drift durch vollen Kontext. Komprimieren ist verlustbehaftet und in Claude Code nicht zuverlässig steuerbar. Deshalb wird vorgebeugt statt komprimiert, in drei Stufen:

1. **Schlank halten.** Der Lead liest keine vollständigen Berichte, nur Status. Reviewer, Tester und Compliance schreiben Ergebnisse in Dateien und geben knapp zurück, z. B. „bestanden“ oder „3 Befunde, Details in Datei X“. Wichtig: Die Abschlussnachricht eines Subagents landet vollständig im Kontext des Lead. Jeder Rollen-Prompt begrenzt sie deshalb hart auf drei Zeilen, und der Frontmatter-Hook prüft, dass die zugehörige Datei existiert und vollständig ist. Vertrauen in den Prompt allein reicht nicht.
2. **Zwischenabschluss nach Arbeitseinheiten.** Nach jedem Vorhaben oder einer festen Zahl von Aufgaben schreibt der Lead eine Zwischenübergabe und beendet sich. Ein Skript startet einen frischen Lead, der nur diese Übergabe liest. Das ist deterministisch und hängt nicht von einer Kontextmessung ab.
3. **Prozent-Alarm als Sicherheitsnetz.** Umgesetzt am 2026-09-21 als PostToolUse-Hook, der die exakte Kontextgröße aus dem Transkript liest und ab der Schwelle eine Anweisung in den Kontext gibt. Ein Hook liest nach jedem Werkzeugaufruf die Kontextgröße. Hooks bekommen den Pfad zum Session-Transkript; aus den Usage-Feldern der letzten Assistentennachricht lässt sich der Kontext exakt berechnen, nicht nur schätzen. Hooks bekommen außerdem Agent-ID und Agent-Typ, der Alarm kann also gezielt auf den Lead reagieren. Über der Schwelle, anfangs etwa 50 %, weist er den Lead an: aktuelle Aufgabe sauber abschließen, Zwischenübergabe schreiben, beenden. Eigenkonstruktion, muss erprobt werden.

Auto-Compact bleibt nur die letzte Rückfallebene. Greift der Prozent-Alarm regelmäßig, sind die Arbeitseinheiten zu groß oder der Lead liest zu viel.

## Schutz gegen Abkürzungen

Agenten neigen dazu, den billigsten Weg zu einem Ergebnis zu nehmen, das erledigt aussieht, oder zu früh aufzuhören. Das ist kein Charakterzug, sondern ein systematisches Risiko aus dem Training. Das System begegnet ihm strukturell, nicht mit Appellen.

| Risiko | Gegenmaßnahme |
| --- | --- |
| Tests werden passend gemacht statt das Problem gelöst | Tester schreibt Tests vorab; Entwickler darf sie nicht ändern |
| „Fertig“ ohne echten Abschluss | Nachweispflicht und Hook, der bei roten Tests den Abschluss blockiert |
| Formal erfüllt, inhaltlich verfehlt | Reviewer prüft gegen die ursprünglichen Akzeptanzkriterien des PO |
| Beschönigte Fortschrittsberichte | Auditor vergleicht Übergabenotiz und Code |
| Drängen zum Abschluss bei vollem Kontext | Kleine Aufgaben mit frischem Kontext |
| Unscharfe Fertig-Kriterien | Planer liefert pro Aufgabe prüfbare Kriterien |
| Alle Aufgaben grün, Problem nicht gelöst | Abnahmetests aus den Akzeptanzkriterien, vor der Planung geschrieben |
| Falscher Test wird formal erfüllt statt angefochten | Testeinspruch als fester Status mit Rücklauf über den Planer |
| Festgefahrener Entwickler drückt durch | Budget pro Aufgabe per Hook, danach Neuschnitt statt Runde drei |
| Review-Churn: jede Runde neue Befunde | Reviewer sieht Vorbefunde, neue Befunde in Runde zwei nur bei hohem Schweregrad |

## Schutz gegen technischen Drift

Agenten verlieren gewählte Architekturmuster, Designsysteme und Strukturkonventionen leicht aus dem Blick, weil sie sich am Code in ihrer Nähe orientieren. Konventionen werden deshalb auf drei Ebenen verankert, von stark nach schwach. Welche Muster und Werkzeuge konkret gelten, wird pro Projekt entschieden und als ADR festgehalten.

1. **Konventionen als Code.** Alles, was sich maschinell prüfen lässt, läuft als Prüftor beim Abschluss jeder Aufgabe und blockiert bei Verstoß, genau wie rote Tests. Typische Bereiche:
   - Schichten- und Modulgrenzen: Welche Teile dürfen welche importieren?
   - Designsystem: Nur Tokens und Komponenten aus der eigenen Bibliothek, keine rohen Werte.
   - Struktur: Generatoren oder Vorlagen legen neue Module, Features und Komponenten im festgelegten Aufbau an, statt sie jedes Mal neu zu erfinden.
2. **Referenzbeispiele.** Pro Muster ein kanonisches Beispiel im Code, etwa ein vollständiger Feature-Schnitt durch alle Schichten. Das Architekturdokument verweist darauf, der Planer gibt jeder Aufgabe den passenden Verweis mit. Abweichungen werden zügig aufgeräumt, bevor sie selbst zur Vorlage werden.
3. **Prosa im Architekturdokument.** Nur für das, was sich nicht prüfen lässt: das Warum hinter den Regeln und die Abwägungen.

**Faustregel:** Jede Konvention, die zweimal manuell korrigiert werden musste, wird zur Prüfregel.

### Verteilung der Regeln

Lint- und Prüfregeln gelten nicht nur für Agenten, sondern auch für CI, IDE und Menschen. Sie liegen deshalb nicht im Plugin, sondern werden in drei Schichten verteilt:

1. **Basisregeln pro Sprache als eigenes Paket.** Versionierte, teilbare Konfigurationen, z. B. als npm-Paket für JavaScript/TypeScript oder als Composer-Paket für PHP. Sie bilden den festen Rahmen, der mit dem System mitkommt.
2. **Projektregeln im Repo.** Die Konfigurationsdatei des Projekts erweitert das Basispaket und ergänzt nur Projektspezifisches, vor allem die Schichten- und Modulgrenzen.
3. **Das Plugin verbindet beides.** Es liefert den Hook, der die Prüfung als Prüftor ausführt, den Skill zum Lesen der Ergebnisse und den Init-Befehl, der das passende Basispaket installiert und eine erweiternde Konfiguration anlegt.

Eine neue Version der Basisregeln ist eine Justierung am Motor und damit ein System-ADR. Projekte übernehmen sie über ein normales Paket-Update. Bewährt sich eine Projektregel, kann sie ins Basispaket wandern.

## Werkzeuge und Skills

Die Bedienung von Werkzeugen wird einmal als Skill festgehalten, damit kein Agent jedes Mal seinen eigenen Weg sucht. Beispiele sind Tests ausführen, Datenbank starten, Paketmanager, Git-Ablauf und die GitHub CLI. Verantwortlich ist der Architekt, denn Tool-Skills sind Konventionen als Code.

| Geltungsbereich | Beispiele | Ort | Pflegt | Änderungen entscheidet |
| --- | --- | --- | --- | --- |
| Allgemein | Git-Ablauf und Commit-Konventionen, PRs per GitHub CLI, Tagesabschluss | Plugin | Architekt, System-Coach | Ich |
| Projektspezifisch | Tests ausführen, Datenbank starten, Paketmanager-Befehle, Startcheck | Projekt, `.keel/skills/` | Architekt | Architekt, bei Tragweite PO |
| Schnittstellen | Backlog-Skript mit Adaptern für Markdown, GitHub Issues, Linear | Plugin | Architekt | Ich (System-ADR pro Adapter), Anbieterwahl pro Projekt als Projekt-ADR |

- **Skripte statt Prosa.** Ein Skill verweist möglichst auf ein Skript statt auf eine Befehlsfolge, z. B. ein Test-Skript, das Abhängigkeiten startet, die Tests ausführt, eine knappe Zusammenfassung ausgibt und Details in eine Logdatei schreibt. Der Skill erklärt nur, wann das Skript genutzt wird und wie die Ausgabe zu lesen ist.
- **Ein Weg für alle.** Prüftore und Hooks rufen dieselben Skripte auf wie die Agenten.
- **Startcheck als Skript.** Umgebung hochfahren und Basis-Test ausführen, bevor neue Arbeit beginnt.
- **Bedarf erkennen.** Der Lead vermerkt Werkzeugprobleme in der Übergabenotiz. Faustregel: Suchen Agenten zweimal nach dem Weg, wird daraus ein Skill.
- **Aktuell halten.** Der Architekt prüft in der Wochenrunde, ob die Skills noch stimmen, etwa nach einem Wechsel von Testumgebung oder Paketmanager.

Geklärt: Claude Code findet Projekt-Skills nur unter `.claude/skills/` (und in `--add-dir`-Verzeichnissen); ein Setting für weitere Ordner gibt es nicht. Die Skills liegen deshalb unter `.keel/skills/` und `.claude/skills` ist ein Symlink darauf. Der Init-Befehl legt den Symlink an. „Extrahieren heißt einen Ordner verschieben“ bleibt damit gültig.

### Backlog als Schnittstelle

Das System legt fest, was es vom Backlog braucht, nicht welches Werkzeug dahinter steht. Das Backlog ist ein Port mit austauschbaren Adaptern: Markdown-Datei im Repo als Standard, GitHub Issues, Linear oder ein anderer Anbieter bei Bedarf. Die Rollen kennen nur das Skript.

**Der Vertrag.** Er ist bewusst klein, weil die Rollen wenig brauchen. Der PO braucht das nächste Element, dessen Inhalt, einen Statuswechsel und die Möglichkeit, Vorschläge einzustellen. Der Auditor braucht die Liste offener Elemente für den Wochenlauf. Der Coach braucht Alter und Durchsatz. Ich priorisiere in der Oberfläche des Werkzeugs, nicht über das System.

```
backlog next                  → höchstpriorisiertes Element mit Status "bereit"
backlog show <id>             → Titel, Problem, Warum, Herkunft, Verweise
backlog list [--status …]     → Elemente als JSON
backlog propose <datei>       → neues Element mit Status "vorgeschlagen", Herkunft PO oder Audit
backlog status <id> <status>  → Statuswechsel innerhalb des kanonischen Satzes
backlog link <id> <vorhaben>  → Verweis auf die Plan-Datei
```

**Kanonische Zustände:** vorgeschlagen, bereit, in Arbeit, erledigt, verworfen. Mehr nicht. Jeder Adapter bildet diese fünf auf seine Welt ab, bei GitHub auf Labels, bei Linear auf Workflow-States, beim Markdown-Adapter auf Abschnitte in der Datei. Die Abbildung steht in `.keel/config.yaml`.

**Datenmodell eines Elements:** ID des Anbieters, Titel, Problem, Warum, Herkunft (Ich, PO, Audit), Status, Rang, Verweise auf Plan-Datei und ADRs. Der Vertrag verlangt nur, was jeder Anbieter kann: geordnete Liste, Status, Text, Verweise. Abhängigkeiten zwischen Elementen, Schätzungen und Zyklen bleiben draußen. Wer das braucht, hat es in der Plan-Datei.

Regeln:

- **Skript statt MCP-Server.** Die MCP-Server von Linear und GitHub laden Dutzende Werkzeugschemas in den Kontext jeder Rolle, erlauben beliebige Operationen inklusive Löschen, und Hooks können sie nicht aufrufen. Das Skript mit sechs Unterbefehlen ist eng, deterministisch und für Agenten wie Hooks derselbe Weg. Es ist zugleich die Berechtigungsgrenze: Der PO bekommt das Skript, nie den rohen API-Zugang. Das zahlt auf Risiko 8 ein.
- **Das Werkzeug besitzt nur Reihenfolge und Status.** Beim Start eines Vorhabens friert der PO Problemstellung und Kriterien in der Plan-Datei ein. Danach ist das System ohne das Werkzeug reproduzierbar, und `git blame` funktioniert weiter für alles, was Entscheidungen betrifft.
- **Vorhaben-ID vom Anbieter entkoppelt.** Die Plan-Datei verweist im Frontmatter auf das Element, die Vorhaben-Nummer bleibt systemintern, siehe Aufgabenzyklus.
- **Adapter sind Motor, Anbieterwahl ist Projekt.** Adapter liegen im Plugin und werden vom Architekten gepflegt, ein neuer Adapter ist ein System-ADR. Welchen Anbieter ein Projekt nutzt, steht in der Konfiguration und ist ein Projekt-ADR. Der Markdown-Adapter ist Standard und braucht keine Konfiguration, damit `init` in einem leeren Projekt sofort läuft.
- **Zugangsdaten außerhalb des Repos.** Anbieter-Tokens liegen in der Umgebung, etwa über `gh auth` oder eine Umgebungsvariable. Die richte ich ein, nicht die Agenten.
- **Audit-Befunde auf Produktebene werden Vorschläge.** Der Auditor stellt sie per `propose` mit Herkunft Audit ein, der PO entscheidet am Tagesstart, ob sie bereit werden. Befunde auf Aufgabenebene gehen weiter in die Plan-Datei.

Der Wochenlauf des Auditors liest das Backlog damit über das Skript statt aus einer Datei. Das ist vertretbar, weil er ohnehin viel lesen darf und danach endet.

**Nicht über diesen Port:** die Entscheidungs-Inbox. Vorlagen haben ein festes Format, das ein Hook prüft, und gehören mit `git blame` zur Historie. Falls ich Vorlagen später unterwegs in der App eines Anbieters abarbeiten will, wird das ein zweiter Port „Inbox“ mit denselben Adaptern, kein Umweg über das Backlog.

## Risikoregister

Die häufigsten Fehlerquellen aus Experimenten mit autonomen Agenten, mit dem Stand ihrer Abdeckung in diesem Konzept. Eine Studie zu Multi-Agenten-Systemen fand, dass rund vier Fünftel der Fehler aus Spezifikation und Koordination stammen, nicht aus dem Modell ([Cemri et al.](https://arxiv.org/abs/2503.13657)). Der System-Coach pflegt dieses Register.

| Nr. | Fehlerquelle | Status | Abdeckung bzw. offener Punkt |
| --- | --- | --- | --- |
| 1 | Spezifikation und Zerlegung: unklare Rollen, zu viel auf einmal, fehlende Abbruchkriterien | abgedeckt | Rollen mit Grenzen, Planer, Fertig-Kriterien |
| 2 | Übergaben: Kontextverlust, Formatfehler, ignorierter Input | abgedeckt | Feste Artefakte mit YAML-Frontmatter, Hook prüft Pflichtfelder an der Grenze; Abschlussnachrichten der Subagents hart begrenzt |
| 3 | Voreiliges „fertig“, fehlende Ende-zu-Ende-Prüfung | abgedeckt | Abnahmetests pro Vorhaben inkl. E2E aus Nutzersicht, Aufgabentests, Prüftore, Nachweispflicht, PO nimmt gegen Abnahmenachweis ab |
| 4 | Kaputter Zustand zwischen Sessions | abgedeckt, erprobt | Startcheck in Tagesstart und Vorhaben, Rot erzeugt Reparaturaufgabe `R-<Datum>`, Tagesabschluss nur an Aufgabengrenzen. Erprobt am 2026-09-21 mit simuliertem Defekt: eine Zeile, ein Commit |
| 5 | Regressionen durch neue Features | abgedeckt | Aufgabentests pro Aufgabe, gesamte Suite vor Abnahme und vor dem Audit |
| 6 | Doppelte Implementierungen | teilweise | Architekt, Referenzbeispiele. Offen: feste Duplikatsprüfung in der Wochenrunde |
| 7 | Kontextverschmutzung durch Werkzeugausgaben, Zeitblindheit | teilweise | Tool-Skills mit Skripten: knappe Ausgaben, Details in Logdateien. Offen: grep-bare Fehlermarken, schnelle Stichproben-Modi für Tests |
| 8 | Destruktive Aktionen, z. B. gelöschte Produktionsdaten | abgedeckt, Punkt 1 der Einführung | Kein Produktionszugang für Agenten, destruktive Befehle per Deny-Regel gesperrt, isolierte Umgebungen, getestete Backups. Kein autonomer Lauf, bevor das steht |
| 9 | Unehrliche Berichte, erfundene Ergebnisse | abgedeckt, erprobt | Nachweispflicht, Auditor vergleicht Übergabenotiz und Code. Erster Audit am 2026-09-21 fand eine Erledigt-Zeile, die der Commit nicht deckte |
| 10 | Tests passend gemacht statt Problem gelöst | abgedeckt | Tests vorab vom Tester, Änderungsverbot für den Entwickler |
| 11 | Technischer Drift | abgedeckt | Konventionen als Code, Referenzbeispiele, Architekt |
| 12 | Veraltende Schutzmaßnahmen nach Modellwechsel | abgedeckt | Modell je Rollenlauf in den Ereignissen, Wechsel als Hinweis beim Start, Coach vorgezogen nach zehn Läufen auf dem neuen Modell und per Hook zur Bewertung angehalten; Umfeld-Recherche nach neuen Modellen. System-ADR 0015 |
| 13 | Uneinheitliche Werkzeugnutzung | abgedeckt | Tool-Skills mit Skripten, Architekt als Verantwortlicher |
| 14 | Festgefahrene Aufgaben ohne Abbruch | abgedeckt | Budget pro Aufgabe per Hook, max. zwei Review-Runden, danach Neuschnitt |
| 15 | Kumulierte Produktdrift über viele unauffällige Tage | abgedeckt | Wochenlauf des Auditors gegen den Gesamtstand |
| 16 | Falsche Tests werden zur Spezifikation | abgedeckt | Reviewer prüft den Test-Diff, Testeinspruch des Entwicklers |
| 17 | Abhängigkeiten mit bekannten Lücken | abgedeckt | Abhängigkeits-Scan und Lockfile-Prüfung als Compliance-Hook |
| 18 | Kennzahlen nicht zuordenbar | abgedeckt | Aufgaben-ID als Schlüssel in Plan, Branch, Commit, Review und Logs |
| 19 | Secrets, ungeplante Abhängigkeiten, personenbezogene Daten im Diff | abgedeckt | Compliance-Scan beim Beenden jedes Entwicklers, Compliance-Rolle bei Ermessensfragen, System-ADR 0010 |

Zu Nr. 8 als Warnbeispiel: Ein Coding-Agent löschte während eines ausdrücklichen Code-Freezes eine Produktionsdatenbank und meldete danach fälschlich bestandene Tests ([Fortune](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure)).

## Kennzahlen und Lernschleife

Das System misst sich selbst, damit es später gezielt nachjustiert werden kann. Die Kennzahlen dienen nur mir und dem System-Coach, nie den arbeitenden Rollen.

### Prinzipien

- **Aus der Arbeit messen, nicht aus Meldungen.** Kein Agent meldet Kennzahlen. Sie werden per Skript aus Artefakten abgeleitet, die ohnehin entstehen: Statuswechsel, Diffs, Review-Befunde, ADR-Status, `decisions/`, Session-Logs.
- **Die Aufgaben-ID ist der Schlüssel.** Plan, Branch, Commit-Trailer, Aufgaben-Datei, Review und Hook-Logs tragen dieselbe ID. Nur so lassen sich Tokens, Befunde, Budgetstand und Rücklauf einer Aufgabe zuordnen. Ein Skript, das Artefakte ohne ID findet, meldet das als Formfehler.
- **Feste Formate aus Arbeitsgründen.** Der Reviewer listet Befunde strukturiert, weil der Entwickler sie braucht. Dass sie zählbar sind, ist ein Nebeneffekt.
- **Außer Sichtweite.** Die Kennzahlen liegen außerhalb des Repos, z. B. unter `~/.keel-metrics/<projekt>/`. Sie tauchen in keinem Rollen-Prompt auf, und arbeitende Rollen haben keinen Lesezugriff.
- **Gegenkennzahlen von anderen.** Jede Kennzahl wird mit einer gepaart, die die betroffene Rolle nicht beeinflussen kann.
- **Korridore statt Grenzwerte.** Zu niedrig kann genauso ein Warnsignal sein wie zu hoch.

### Kennzahlen

Die Korridore sind Startwerte und werden nach den ersten Wochen kalibriert.

| Bereich | Kennzahl | Gegenkennzahl | Korridor (Start) | Quelle |
| --- | --- | --- | --- | --- |
| Meine Aufmerksamkeit | Vorlagen pro Woche | Auditor-Befunde zu delegierten Entscheidungen | 2–5 | `decisions/` |
| Meine Aufmerksamkeit | Zeit bis zur Entscheidung | – | < 2 Tage | `decisions/` |
| PO-Kalibrierung | Anteil gekippter delegierter ADRs | – | < 10 % | ADR-Status |
| Planung | Aufgabengröße | Anteil neu geschnittener Aufgaben | offen | Diff, Aufgabenstatus |
| Umsetzung | Rücklaufquote im Review | Spätere Bugfixes auf abgeschlossene Aufgaben | offen | Statuswechsel, Git |
| Umsetzung | Review-Runden pro Aufgabe | – | ≤ 2 | Statuswechsel |
| Abkürzungen | Blockierte „fertig“-Meldungen | – | offen | Hook-Log |
| Abkürzungen | Budgetüberschreitungen pro Woche | Anteil neu geschnittener Aufgaben | offen | Hook-Log, Aufgaben-Dateien |
| Spezifikation | Testeinsprüche pro Woche | Anteil berechtigter Einsprüche | offen | Aufgaben-Dateien |
| Abnahme | Vorhaben mit rotem Abnahmenachweis trotz grüner Aufgaben | – | möglichst 0 | Abnahmenachweise |
| Technischer Drift | Verstöße gegen Architekturregeln pro Woche | Drift-Befunde des Architekten in der Wochenrunde | offen | Hook-Log |
| Werkzeuge | Fehlgeschlagene und wiederholte Befehle pro Aufgabe | Werkzeugprobleme in Übergabenotizen | offen | Befehls-Log |
| Kontext | Auslösungen des Prozent-Alarms beim Lead | – | möglichst 0 | Hook-Log |
| Drift | Abweichungen Übergabenotiz vs. Code | – | offen | Prüfberichte |
| Kosten | Tokens pro Aufgabe und Tag | – | offen | Session-Logs |
| Backlog | Durchlaufzeit von bereit bis erledigt | Zahl der Elemente mit Status bereit | offen | Backlog-Skript |

### Lernschleife

1. Hooks schreiben Rohdaten täglich fortlaufend in den Kennzahlen-Ordner.
2. Der System-Coach läuft monatlich oder sobald eine Kennzahl ihren Korridor verlässt.
3. Er wertet Kennzahlen und Risikoregister aus und recherchiert anhand der Referenzliste, was sich im Umfeld getan hat.
4. Jeder Vorschlag enthält eine Hypothese, z. B.: „Aufgaben auf maximal 200 Diff-Zeilen begrenzen, erwartet: Rücklaufquote sinkt unter 20 %.“
5. Ich entscheide. Angenommene Justierungen werden als System-ADR festgehalten und im Plugin umgesetzt.
6. Beim nächsten Lauf prüft der Coach, ob die Hypothese eingetreten ist.

## Umsetzung in Claude Code

Für den sequenziellen Ablauf reichen Subagents. Agent Teams sind nicht nötig und würden deutlich mehr Tokens kosten. Subagents können selbst Subagents aufrufen, standardmäßig bis drei Ebenen tief. Genutzt wird das trotzdem nicht: Der Lead ruft alle Rollen selbst der Reihe nach auf, auch die Runden zwischen PO und Architekt. Flache Aufrufe mit Dateiübergabe sind nachvollziehbar und zählbar, verschachtelte nicht.

| Baustein | Umsetzung |
| --- | --- |
| Rollen | Je eine Agent-Definition im Plugin, mit eigenem Prompt und erlaubten Tools, z. B. Reviewer nur lesend. Jede Rolle endet mit einer Abschlussnachricht von höchstens drei Zeilen |
| Lead | Haupt-Session, die alle Subagents flach und der Reihe nach aufruft, auch den PO |
| Planer | Subagent mit Lesewerkzeugen und Schreibrecht nur auf die Plan-Datei. Das ersetzt den Plan-Modus, der für die Haupt-Session gedacht ist |
| Prüftore | Hooks im Plugin: Tests, Compliance-Checks, Frontmatter-Prüfung und Budget beim Abschluss einer Aufgabe. Die Startbedingungen der Rollen stehen als Tabelle in `scripts/flow.py`; `tests/gate/` prüft das Gate gegen den vorigen Stand |
| Sichtbarkeit | `/keel:hilfe` erklärt den Stand auf Abruf, `/keel:monitor` zeigt ihn laufend als lokale Webseite; beide lesen nur |
| Sicherheit | Deny-Regeln in `.claude/settings.json` für destruktive Befehle, Produktions-Credentials nicht in der Umgebung |
| Kennzahlen-Sperre | Agent-Definitionen können nur Werkzeuge einschränken, keine Pfade. Pfad-Deny-Regeln gelten sessionweit. Die Sperre des Kennzahlen-Ordners für arbeitende Rollen ist deshalb ein PreToolUse-Hook, der Agent-Typ und Pfad prüft und alles außer dem Coach abweist |
| Tool-Skills | Allgemeine im Plugin, projektspezifische unter `.keel/skills/` mit Symlink aus `.claude/skills/`, jeweils mit Skripten |
| Kennzahlen | Hook-Skripte im Plugin, die Rohdaten aus Artefakten anhand der Aufgaben-ID ableiten und außerhalb des Repos ablegen |
| Backlog | Skript im Plugin mit Adaptern, Standard Markdown; Anbieter in `.keel/config.yaml`; PO und Auditor bekommen das Skript als Skill, keinen MCP-Server |
| Abläufe | Befehle im Plugin, z. B. Tagesabschluss, Audit, Coach-Lauf, Init |
| Gemeinsames Wissen | `.keel/CLAUDE.md`, per Import in die Projekt-`CLAUDE.md` eingebunden |
| Tagesstart | Frische Sessions, die nur aus den Dateien laden, beginnend mit dem Startcheck |

### Installation in Projekten (Idee)

Das System wird in zwei Teile getrennt: den **Motor**, der für alle Projekte gleich ist, und die **Projektdaten**, die zu genau einem Repo gehören.

- **Motor als Claude-Code-Plugin:** Rollen, Hooks, Vorlagen für ADRs, Vorlagen und Prüfberichte sowie Befehle liegen in einem eigenen Repo, das zugleich als Marketplace dient. Verbesserungen erfolgen zentral und werden mit `claude plugin update` in alle Projekte übernommen.
- **Basisregeln als Pakete:** Lint- und Prüfregeln pro Sprache liegen als versionierte Pakete vor, nicht im Plugin, damit sie auch für CI, IDE und Menschen gelten. Siehe Verteilung der Regeln.
- **Projektdaten im Namensraum-Ordner:** Alles Projektspezifische liegt unter `.keel/` und ist mit dem Code versioniert.
- **Brücke per Import:** Die bestehende Projekt-`CLAUDE.md` bekommt nur die Zeile `@.keel/CLAUDE.md`.

Installation pro Projekt:

```
claude plugin marketplace add <github-user>/keel
claude plugin install keel@<marketplace> --scope project
```

Mit `--scope project` landet im Projekt nur ein Eintrag unter `enabledPlugins` in `.claude/settings.json`. Ein Befehl wie `/keel:init` legt in neuen Projekten die Ordnerstruktur mit leeren Vorlagen an.

Jedes Projekt hat damit vier Berührungspunkte: den Eintrag und die Deny-Regeln in `settings.json`, eine Zeile in `CLAUDE.md`, den Ordner `.keel/` und den Symlink `.claude/skills`.

Hinweis: Laut Erfahrungsberichten wird ein Plugin nicht zuverlässig automatisch installiert, nur weil es in `settings.json` eingetragen ist. Den Install-Befehl einmal pro Rechner selbst ausführen.

### Einführung

- [x] Sicherheit zuerst: Deny-Regeln und Guard-Hook (2026-09-21). Offen pro Projekt: isolierte Umgebung, Backup getestet
- [ ] Zielbild, Qualitätsmerkmale mit Rangfolge, Befugnisse und ein erstes Backlog schriftlich festhalten
- [x] Backlog-Skript mit Markdown- und GitHub-Adapter, beide erprobt (2026-09-21). Linear erst bei Bedarf
- [x] Plugin-Repo `keel` angelegt: alle Rollen des Konzepts als Agents, Lead als Skill (2026-09-21). PO und Architekt mit Abstimmung nachgezogen, Epic-Ebene ergänzt (System-ADRs 0008, 0009)
- [x] Frontmatter-Schema und Prüf-Hooks an Start und Stop jeder Rolle, siehe System-ADR 0001 (2026-09-21)
- [x] Budget-Hook (Werkzeugaufrufe, Diff-Zeilen, Zeit) und Aufgaben-ID in Plan, Aufgaben-Datei, Commit-Betreff und Trailer `Keel-Task` (2026-09-21). Branch pro Vorhaben und Reparatur, siehe System-ADR 0003
- [ ] Basisregeln pro genutzter Sprache als Pakete anlegen
- [x] Init-Befehl `/keel:init` (2026-09-21). Offen: Basisregeln einbinden
- [x] Startcheck in `/keel:tagesstart` und `/keel:vorhaben`, Reparaturaufgabe `R-<Datum>` mit Entwickler und Reviewer, erprobt mit simuliertem Defekt (2026-09-21)
- [x] Tagesrhythmus als Befehle: `/keel:tagesabschluss`, `/keel:audit`, `/keel:inbox`, `/keel:tagesstart` (2026-09-21)
- [x] Neuschnitt durch den Planer bei Testeinspruch, Budget und Befunden nach Runde 2; Vorlage erst beim zweiten Neuschnitt (2026-09-21)
- [x] Plugin im Beispielprojekt installiert, erstes Vorhaben abgenommen (2026-09-21)
- [x] Kennzahlen aus Artefakten und Rohdaten (`metrics.py`), Kennzahlen-Ordner für arbeitende Rollen per Hook gesperrt, nur der Coach liest ihn (2026-09-21)
- [ ] Erste Wochen: enger Spielraum für den PO, Vorlagen und Auditor-Befunde beobachten
- [x] Coach als Rolle mit `/keel:coach`, erster Lauf am 2026-09-21 auf den Daten des ersten Tages; Kalibrierung nach einem Monat echter Nutzung
- [x] Ablauf-Monitor `/keel:monitor` als lokale Webseite, Startbedingungen der Rollen als gemeinsame Tabelle für Gate und Monitor, Regressionstest für das Gate (2026-09-26, System-ADR 0017). Offen: Erprobung im echten Projekt
- [ ] Befugnisse und Maßstäbe nachschärfen, Rollen erst bei Überlastung trennen

## Erkenntnisse aus dem ersten Lauf

Beispielprojekt, Vorhaben V1 „Rechnung mit Steuersätzen“, 2026-09-21, Claude Code 2.1.236:

- 13 Rollenläufe, 10 bis 21 Werkzeugaufrufe je Rolle, keine blockierte Übergabe, kein Budgetverstoß, jede Abschlussnachricht innerhalb von drei Zeilen. Die Hooks haben also nicht korrigieren müssen; die Prompts reichten. Ob das so bleibt, zeigt die Kennzahl `stop_blocked`.
- Drei Aufgaben, drei Reviews in Runde 1 bestanden, Abnahmetests 5 von 5 grün.
- Ein berechtigter Testeinspruch: Der Planer hatte eine vierte Aufgabe „Abnahme absichern“ geschnitten, deren Kriterium Testdateien gegen ihre eigene Import-Zeile prüfte. Tester vermerkte den Widerspruch, Entwickler legte Einspruch ein statt drumherum zu bauen, Lead brach ab und meldete. Korrektur an den Maßstäben: Der Planer darf keine Prozessaufgaben schneiden, die Abnahme ist Schritt des Lead. Der Einzelfall wurde als PO verworfen und dokumentiert.
- Der Tester hält Lücken in den Kriterien als „Anmerkung des Testers“ fest, der Planer entscheidet sie im Plan. Das ersetzt die direkte Absprache und funktioniert.
- Der Reviewer erbringt den Nachweis selbst, statt dem Entwickler zu glauben. Seine Anmerkungen ohne Kriterienbezug blockieren nicht.

## Erkenntnisse aus dem Tagesrhythmus

Erster Durchlauf von Tagesabschluss, Audit, Inbox, Tagesstart mit Reparatur, 2026-09-21:

- Der Tagesabschluss aus einer frischen Session funktioniert: Übergabenotiz nur aus Git-Log und Frontmatter, Tag gesetzt. Eine Erledigt-Zeile war ungenau, weil ein Commit-Betreff mehr versprach als sein Inhalt.
- Der Auditor hat mit 39 Werkzeugaufrufen acht Befunde geliefert, sechs davon berechtigt und konkret mit Fundstelle: fehlendes ADR für eine delegierte Entscheidung, veraltete Plantabelle, leeres Backlog trotz Verweis, Platzhalter in der Kurzfassung. Zwei Befunde betrafen den Entwicklungsablauf des Plugins selbst (Arbeitsbaum, Prompt außerhalb des Repos) und wurden Vorlagen. Das Format hat gehalten: kein Freitext, jede Abweichung mit Vorschlag Aufgabe oder Vorlage.
- Der Auditor findet, was Menschen bei manueller Nacharbeit übersehen. Die Regel „Korrekturen gehen an die Maßstäbe“ gilt auch für den Menschen: Meine PO-Entscheidung ohne ADR war der erste Befund.
- Startcheck rot durch einen simulierten Defekt: Reparaturaufgabe, Entwickler mit 9 Aufrufen auf die eine Zeile, Reviewer bestanden, Commit. Kein Eingriff nötig.
- Neuschnitt erprobt mit simuliertem Testeinspruch (V2): Der Planer entschied „Test falsch, Kriterium richtig“, schärfte das Kriterium mit Erwartungswert, leerte die Tests; Tester, Entwickler, Reviewer und Abnahme liefen danach ohne Eingriff durch. Ein erster Versuch mit committeten strittigen Tests ließ den Lead korrekt abbrechen, weil Startcheck und Neuschnitt sich widersprachen; im echten Ablauf sind Tests bis zum Review nie committet. Ergänzt: Der Lead erkennt unbestätigte Dateien einer laufenden Aufgabe als erwarteten Zwischenstand nach einem Sessionabbruch.
- Bei der Abnahme von V1 und V2 zwei Qualitätsbefunde: Das Pflichtfeld `steuersatzProzent` änderte die öffentliche Schnittstelle von `Position` ohne Vorlage; jetzt legt der Planer dafür einen ADR-Entwurf an, den die Inbox zeigt. Und Abnahmetests liefen nach der Abnahme in keinem Prüftor mehr; jetzt wandern sie bei der Integration in die Regressionssuite.
- Zwei Auditor-Befunde betrafen den Entwicklungsablauf des Plugins: unsauberer Arbeitsbaum durch das Deaktivieren des installierten Plugins, und Verweise auf Prompts außerhalb des Repos. Beides wurde eingearbeitet: Entwicklungsläufe nutzen ein Settings-Override, und der Auditor behandelt Verweise auf den Motor als außerhalb des Prüfumfangs.
- Für Entwicklungsläufe des Plugins gegen ein Projekt mit installierter Version: `--plugin-dir` plus `--settings '{"enabledPlugins":{"keel@keel":false}}'`, damit der Arbeitsbaum sauber bleibt. Der Auditor hatte den unsauberen Baum sofort gemeldet.

## Erkenntnisse aus der Lernschleife

Erster Coach-Lauf und Kennzahlen am 2026-09-21, nach einem Tag Betrieb im Beispielprojekt:

- Die Kennzahlen lassen sich vollständig aus Artefakten ableiten; keine Rolle meldet etwas. Zwei Korridore waren am ersten Tag verletzt: „Vorlagen pro Woche“ bei 0, weil der Mensch als PO direkt entschieden hat, und „Audit-Abweichungen pro Bericht“ bei 8, weil der erste Audit Aufbauarbeit prüfte. Beides sind Startphänomene, keine Systemfehler; der Coach soll das erkennen.
- Der GitHub-Adapter arbeitet mit Labels `keel:<status>` und schließt Issues bei erledigt oder verworfen. Das Löschen von Issues gibt es nicht, das Skript kennt keinen solchen Befehl.

## Zwei Befehle

Ergänzt am 2026-09-22. Ich merke mir keine Befehle: `/keel:start` liest, was fällig ist, holt Versäumtes nach, wird zum Briefing, wenn eines aussteht, und arbeitet sonst am nächsten Vorhaben; `/keel:stop` schließt den Tag mit Übergabenotiz, Tag und Audit ab. Fälligkeiten wie Coach und Architektur-Runde entstehen aus dem Zustand, mit Schwellen für genug Betrieb, und ein Hook erzwingt sie. Siehe System-ADR 0012.

## Hilfe statt Stützräder

Ergänzt am 2026-09-26. Für die ersten Wochen im echten Projekt stand eine Proxy-Session über keel zur Debatte, die beaufsichtigt, korrigiert und Vorlagen durchreicht. Verworfen: Es gibt genau einen Entscheider, und die Vorlage wartet auf ihn; eine zweite Aufsicht verwischt die Kalibrierung von Supervisor und Coach. Geblieben ist `/keel:hilfe`, eine Skill ohne Befugnisse: Sie erklärt den Stand aus Zustand und Ereignissen, nennt den nächsten Befehl und darf mit meinem Ja Reste aufräumen, einen Hinweis für den Coach ablegen oder einen Motor-Befund melden. Motor-Reparaturen finden im Plugin-Repo statt, nie im Projekt. Siehe System-ADR 0014; seit System-ADR 0021 gehen Motor-Befunde und Motor-Vorschläge nicht mehr als Issue in das öffentliche Plugin-Repo, sondern in die lokale Motor-Ablage `~/.keel-metrics/motor/`.

## Modellwechsel

Ergänzt am 2026-09-26, als Opus 5.5 seit Tagen verfügbar war und keel es nicht bemerkt hatte. Jeder Rollenlauf schreibt jetzt sein Modell mit. Läuft eine Rolle auf einem neuen Modell, nennt der Sessionstart das als Hinweis. Nach zehn Läufen auf dem neuen Modell wird der Coach fällig, auch vor Ablauf seiner 30 Tage, vergleicht je Rolle altes und neues Modell und schlägt Änderungen als Vorlage vor. Welches Modell eine Rolle bekommt, steuert keel noch nicht; als nächsten Schritt schlägt System-ADR 0016 Komplexitätsstufen vor: Der Planer stuft jede Aufgabe ein, die Konfiguration ordnet Stufen Modellen zu, und bei Belegen wird eine Stufe höher eskaliert. Siehe System-ADR 0015 und 0016.

## Ablauf-Monitor

Ergänzt am 2026-09-26. keel lief still im Hintergrund: Wer gerade arbeitet, wer als Nächstes dran ist und warum etwas steht, war nur über `/keel:hilfe` oder durch Lesen der Dateien zu erfahren. `/keel:monitor` zeigt das laufend als lokale Webseite: ein Ablaufdiagramm mit jeder Rolle als aktiv, bereit oder gesperrt, die laufende Rolle mit dem Befehl, in dem der Lead sie rief, Fälligkeiten, Vorlagen, einen Ereignisstrom mit den Gründen für Blockaden, je Vorhaben eine Zeitleiste von der Problemstellung bis zur Abnahme und alle Übergaben als lesbare Dokumente. Er beobachtet nur, wie die Hilfe. „Wer kommt als Nächstes“ beantwortet er als Regel, nicht als Vorhersage: bereit ist eine Rolle, deren Startbedingung erfüllt ist; welche davon der Lead ruft, bleibt seine Entscheidung. Damit Anzeige und Gate nicht auseinanderlaufen, stehen die Startbedingungen jetzt in einer Tabelle (`scripts/flow.py`), aus der beide lesen, und ein Regressionstest (`tests/gate/`) vergleicht das Gate vor jeder Änderung mit dem vorigen Stand. Mit `monitor.autostart: true` starten ihn die Befehle, die das System arbeiten lassen, von selbst mit. Siehe System-ADR 0017.

## Review mit Schwelle und Pflegeliste

Ergänzt am 2026-09-30. Fixes nach einem Review haben oft selbst Fehler eingebaut. Weil die Befunde als behoben galten, gingen diese Fehler ohne echtes Review durch. Jetzt gilt eine Umsetzung erst als umgesetzt, wenn das Review unter einer Schwelle bleibt. Jede Nacharbeit wird als eigenes Delta erneut reviewt, und weitere Runden gibt es nur, solange die Befunde sinken, sonst entscheidet der Supervisor. Anmerkungen unter der Schwelle bleiben nicht liegen: Sie landen in einer Pflegeliste. Der Architekt macht in der Wochenrunde daraus Prüfregeln oder gebündelte Pflegeaufgaben, höchstens zwei je Runde, und was niemand aufgreift, verfällt. Siehe System-ADR 0018.

## Fehlervertrag: Gates schließen bei Fehlern

Ergänzt am 2026-10-01 nach einer Prüfung des Kerns. Claude Code blockiert nur, wenn ein Hook mit Exit-Code 2 endet oder ausdrücklich ablehnt; jeder andere Fehler lässt den Aufruf durch. Mehrere Gates haben deshalb still durchgelassen, sobald ein Werkzeug fehlte, ein Feld leer war oder ein Hilfsskript abstürzte. Jetzt gilt ein Fehlervertrag: Skripte des Kerns antworten mit 0 für nein, 1 für ja und 2 für „konnte nicht prüfen“. Gates schließen bei jedem unerwarteten Ende mit einer Meldung, Beobachter protokollieren den Fehler und lassen weiterlaufen. Das Prüftor hat eine eigene Zeitgrenze unter dem Hook-Timeout. Vertragstests unter `tests/contract/` belegen jeden bekannten Fall, eine CI führt sie auf Linux und macOS aus. Siehe System-ADR 0019 und `docs/kern-befunde.md`.

## Supervisor und Morgen-Briefing

Ergänzt am 2026-09-22. Die rechte Hand aus dem Zweck-Abschnitt ist nicht der PO, sondern eine eigene Rolle mit Gesamtbild: Roadmap, Epics, ADR-Historie, Leitlinien und meine früheren Entscheidungen. Tagsüber entscheidet der Supervisor jede Vorlage innerhalb seiner Stufe, damit die Arbeit weiterläuft, und stuft Richtungsfragen als solche ein. Morgens legt er mir in einer eigenen, interaktiven Session vor, was er entschieden hat, hilft beim Kippen, entscheidet mit mir die richtungsweisenden Vorlagen und hält Leitlinien fest, die künftig dieselbe Frage ohne Vorlage beantworten. Ein Gate sperrt alle Rollen, bis das Briefing stattgefunden hat. Die Befugnisse haben damit drei Stufen. Siehe System-ADR 0011.

## Epic-Ebene

Ergänzt am 2026-09-21 nach dem Szenario „Freigabe-Pipeline“ und einer Recherche zu Dach-Artefakten in Anthropic-Harnesses, Cursor, Spec Kit, Kiro und BMAD. Große Themen bekommen vor dem ersten Vorhaben ein Epic: Zielbild des Themas, Vorhaben-Liste, Leitfragen, Done-Condition. Der Architekt bewertet Leitentscheidungen nach Reichweite, also danach, welche Entscheidung im ersten Vorhaben ein späteres wieder umstoßen müsste. Leitentscheidungen werden ADR, außerhalb der Befugnisse des PO als Vorlage an mich, bevor eine Zeile Code entsteht. Nach jeder Integration prüft der Architekt in einer Retrospektive gegen die Leitentscheidungen; eine Kurskorrektur wird eine Vorlage, bevor das nächste Vorhaben geplant wird. Das erste Vorhaben ist immer der dünnste Ende-zu-Ende-Pfad. Siehe System-ADR 0009 und `docs/system.md`.

## Wiedervorlagen und lokale Motor-Ablage

Ergänzt am 2026-10-02 nach dem ersten Probelauf. Offene Fragen gingen verloren, und es gab nur „sperrt alles“ oder „unsichtbar“. Jetzt hat jede offene Frage einen Ort, den ein Skript sieht: Was eine Weichenstellung ist, bleibt eine sperrende Vorlage; was nur wiederkommen soll, wird eine Wiedervorlage mit Termin und steht auf der Tagesordnung des nächsten Briefings, ohne die Arbeit anzuhalten. Eine zurückgestellte Vorlage sperrt beim zweiten Termin wieder. Am Ende des Briefings prüft ein Hook, dass nichts nur im Protokoll steht. Rollen schreiben ADRs nur auf ihrer Stufe, ein Hook vergleicht den Stand vor und nach dem Lauf; auf Feature-Branches entstehen ADRs als Entwurf und bekommen ihre Nummer bei der Integration. Das Zeitbudget meldet nur noch. Vorschläge des Coachs zum Plugin selbst und Befunde aus `/keel:hilfe` gehen nicht mehr als Issue in das öffentliche Plugin-Repo, sondern in eine lokale Ablage für alle Projekte des Rechners; entschieden werden sie im keel-Repo, einmal für alle. Siehe System-ADR 0021 und `docs/arbeitspakete/03-wiedervorlagen.md`.

## Referenzen

Startpunkt der Referenzliste für die Umfeld-Recherche des System-Coachs.

- [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) – Anthropic, 16 parallele Agenten, Lehren zu Tests, Kontext und Rollen
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) – Anthropic, Fehlermuster über mehrere Sessions und Gegenmaßnahmen
- [Scaling Managed Agents](https://anthropic.com/engineering/managed-agents) – Anthropic, warum Schutzmaßnahmen mit neuen Modellen veralten
- [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) – Anthropic, Planer, Generator, Evaluator, Feature-Liste als Vertrag
- [Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) – Cognition, implizite Entscheidungen zwischen Agenten
- [Engineering at Anthropic](https://www.anthropic.com/engineering) – laufende Beiträge zu Agenten und Harnesses
- [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams) – Claude-Code-Doku zu Agent Teams
- [Scaling long-running autonomous coding](https://cursor.com/blog/scaling-agents) – Cursor, Planer, Worker und Judge
- [Towards self-driving codebases](https://cursor.com/blog/self-driving-codebases) – Cursor, Weiterentwicklung mit Executor-Rolle
- [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) – Taxonomie von 14 Fehlermustern
- [The Code Agent Orchestra](https://addyosmani.com/blog/code-agent-orchestra/) und [Long-running Agents](https://addyosmani.com/blog/long-running-agents/) – Addy Osmani, Überblick über Muster und Werkzeuge
- [awesome-agent-orchestrators](https://github.com/andyrewlee/awesome-agent-orchestrators) – gepflegte Liste von Orchestrierungs-Werkzeugen
