# Kontext per Regel statt per Prosa

2026-10-01 · Konzeptentwurf aus dem Brainstorming, noch keine Entscheidung und kein ADR

## Kurzfassung

Welchen Kontext eine Rolle bekommt, soll künftig der Core nach festen Regeln bestimmen, so wie er heute schon Abläufe und Formate regelt. Ein Agent bekommt drei Dinge: seinen Rollenkern (immer gleich, aus der Agentendefinition), den Auftrag für den aktuellen Anlass und den Kontext, den das Profil dieses Anlasses vorsieht. Fachkontext ist nach Modulen geordnet, jedes Modul hat einen inneren Teil und eine Schnittstelle, und Module sind über einen Graphen verbunden. Fehlt einem Agenten Kontext, holt er ihn protokolliert nach oder meldet es. Der Coach wertet diese Abweichungen aus, und daraus lernen die Profile.

Eingeführt wird das in Stufen, beginnend mit einer Messung des heutigen Stands. Gesperrt wird zunächst nichts, Abweichungen werden nur protokolliert.

## Problem

Für Code ist der Kontext heute schon fest: Der Entwickler liest, was im Frontmatter der Aufgabe unter `tests`, `referenz` und `dateien` steht, und sonst nichts. Fachwissen dagegen kommt über `architektur.md` als Ganzes oder über die `Hinweise` des Planers, also über Prosa. Ob eine Rolle das Richtige weiß, hängt davon ab, ob jemand daran gedacht hat, es hineinzuschreiben.

Dazu kommt ein zweites, gleich gelagertes Problem eine Ebene höher. Rollen haben mehrere, sehr unterschiedliche Anlässe. Der Architekt hat sechs in einer Datei mit rund 1300 Wörtern, der PO sieben in rund 1600 Wörtern. Bei jedem Aufruf liest die Rolle die Beschreibung aller Anlässe, obwohl nur einer gerade ihrer ist.

Beides ließe sich deterministisch lösen, denn der Core hat für Abläufe und Formate schon feste Regeln.

## Grundsätze

1. **Der Core bestimmt, nicht ein Modell.** Was eine Rolle bekommt, ergibt sich aus Zuordnungen und Regeln. Ein Fehler darin ist eindeutig und fällt schnell auf.
2. **Geben statt holen lassen.** Pflichtkontext wird mitgegeben. Der Agent entscheidet nicht, ob er ihn liest.
3. **Der Agent darf sagen, dass ihm etwas fehlt.** Er ist kein Abarbeiter. Fehlender Kontext wird nachgeholt oder gemeldet, beides protokolliert. Raten ist schlimmer als Nachfragen.
4. **Breite ohne Tiefe.** Weitsicht braucht den Überblick, was es gibt und was womit verbunden ist. Entscheidungen verwässern durch Inhalte, die nicht betroffen sind.
5. **Feinheit wächst mit dem Projekt.** Ein kleines Projekt hat ein Modul und verhält sich wie keel heute. Mehr Module, Kanten oder Teile kommen nur mit einem Befund dazu, und Rückbau gilt ebenso.
6. **Erst messen, dann sperren.** Neue Regeln protokollieren zuerst nur. Abgelehnt wird erst, wenn die Messung zeigt, dass die Regel stimmt. Das folgt dem Grundsatz aus `konzept.md`, Neues nur bei gemessenem Problem einzuführen.
7. **Kontrolle an den Grenzen, Freiheit innen.** Siehe „Freiheit im Rahmen“.

## Freiheit im Rahmen

Das System ist auf Autonomie ausgelegt. Mitdenken im Rahmen ist gefordert, nicht nur erlaubt. Wie in einer Firma mit Menschen braucht die Zusammenarbeit Regeln, aber wer die Fähigkeiten der Einzelnen wegregelt, bekommt Abarbeiter statt Problemlöser. Ein zu enger Kontext und zu viele Gates würden genau das bewirken.

Die Balance in diesem Konzept:

- **Regeln betreffen Grenzen und Ergebnisse, nicht den Weg.** Deterministisch geregelt ist, was zwischen Rollen und zwischen Modulen passiert: Übergaben, Formate, Schnittstellen, Modulgrenzen, die Ratsche. Wie ein Agent innerhalb seines Moduls ein Problem löst, regelt niemand. Dort zählt sein Urteil.
- **Kontext ist Ausgangslage, kein Käfig.** Pflichtkontext ist das Minimum, nicht das Maximum. Nachholen ist erlaubt und erwünscht, wenn es begründet ist. Protokolliert wird, um zu lernen, nicht um zu bestrafen.
- **Widerspruch ist ein Kanal, kein Regelbruch.** Hält ein Agent eine Regel, einen Zuschnitt oder ein Profil für falsch, hat er feste Wege, das zu sagen: `testeinspruch`, `kontext_fehlt`, ein Kontextvorschlag, ein Befund. Einwände sind eine Pflicht, wie beim Supervisor. Ein Agent, der eine Regel stillschweigend umgeht, ist ein Problem. Einer, der sie begründet anficht, ist erwünscht.
- **Regeln müssen sich ihren Platz verdienen.** Jede Regel hat eine Hypothese und wird gemessen. Löst sie nie aus oder blockiert sie gute Arbeit, schlägt der Coach Rückbau vor. Das gilt für die Gates dieses Konzepts genauso wie für die bestehenden Schutzmaßnahmen.
- **Ein Fehlalarm kostet Vertrauen.** Ein Gate, das gute Arbeit blockiert, lehrt Agenten (und Menschen), Regeln als Hindernis zu sehen. Deshalb erst protokollieren, dann sperren.

Woran man erkennt, dass die Balance kippt:
- **Zu viel Kontrolle:** Agenten melden oft `kontext_fehlt` oder holen ständig nach, Pflichtfelder werden mit Floskeln gefüllt, Gates blockieren häufig ohne echten Befund, Lösungen werden kleinteilig und mechanisch.
- **Zu viel Freiheit:** Die Ratsche greift oft, Grenzverletzungen steigen, Nacharbeit nimmt zu, Entscheidungen verschiedener Aufgaben widersprechen sich.

Beides lässt sich aus den Kennzahlen dieses Konzepts ablesen, und der Coach kann in beide Richtungen nachjustieren.

## Bausteine

### Ablage und Format

- Kontext liegt zentral im Projekt unter `.keel/kontext/`, nicht verteilt neben dem Code. Neben dem Code würden Agenten ihn nebenbei mitlesen, sobald sie eine Datei in der Nähe öffnen, und die Zuordnung wäre nicht mehr kontrollierbar.
- Jedes Dokument trägt Frontmatter: `modul`, `teil` (`innen` oder `schnittstelle`), `kontext` (`pflicht` oder `optional`) und bei Werkzeugen eine `version`.
- Es gibt keine Datenbank. Markdown mit Frontmatter plus ein Index, den der Core beim Scannen erzeugt, bleibt im Git nachvollziehbar.
- Für Pflichtdokumente gibt es eine Größengrenze je Modul.

### Module, Pfade und Graph

- **Module auf Pfade.** In `.keel/config.yaml` steht je Modul, welche Pfade dazugehören, im Glob-Format, wie es Claude Code (`paths`), Copilot (`applyTo`) und Cursor (`globs`) schon nutzen. Je Modul stehen dort auch die Pfade seiner öffentlichen Schnittstelle.
- **Geschlossenes Vokabular.** Erlaubt sind nur Module aus der Konfiguration. Ein Check im Stil von `check_references.py` meldet Dokumente ohne Modul, Module ohne Dokument und Pfade ohne Modul. Pfade ohne Modul blockieren nicht, sie fallen unter einen Auffang-Eintrag und werden gemeldet.
- **Zwei Teile je Modul.** `innen` beschreibt Regeln und Aufbau des Moduls selbst. `schnittstelle` beschreibt, was andere Module nutzen dürfen und worauf sie sich verlassen können.
- **Modulgraph.** Je Modul steht in der Konfiguration, mit welchen Modulen es verbunden ist. Der Architekt pflegt das. Gemeinsame Datenmodelle sind ein eigenes Modul, mit dem die nutzenden Module verbunden sind. Dafür braucht es keine eigene Ebene.
- **Eine Quelle für Kontext und Lint.** Derselbe Graph speist die Prüfung der Modulgrenzen im Projekt-Lint (siehe Technik). Ein Werkzeug, das beides aus einer Quelle macht, hat die Recherche nicht gefunden.
- **Global bleibt.** `architektur.md` bleibt als globaler Rahmen mit Mustern, Grenzen und Referenzbeispielen. Modulkontext kommt dazu, er ersetzt den Rahmen nicht.

### Rollenkern und Auftrag je Anlass

- **Rollenkern** steht in der Agentendefinition unter `agents/`, ist immer dabei und ändert sich nicht je Aufruf. Er sagt: wer die Rolle ist, welchen Platz sie im System hat, ihre Grundsätze, Befugnisse und Grenzen, allgemeine Regeln, den Abschluss. Dazu kommt eine Liste aller Anlässe der Rolle mit je einem Satz. So erkennt die Rolle, wenn jemand etwas verlangt, das nicht ihre Aufgabe ist. Der Kern muss die Haltung tragen, nicht nur die Grenzen.
- **Auftrag je Anlass** liegt als eigene Datei im Plugin, zum Beispiel `auftraege/architekt/kontext.md`, und wird nur für den aktuellen Anlass eingespielt. Er sagt, was genau zu klären ist, was zu lesen ist und in welchem Format die Antwort kommt. Beispiel für den Anlass `kontext`: „Ein Übergang zwischen Modulen wurde erkannt. Kläre, ob er sauber über die Schnittstelle läuft und ob das globale Muster verletzt ist.“
- Teile, die mehrere Anlässe gemeinsam nutzen, etwa das Format der Epic-Bewertung, das auch die Epic-Retrospektive braucht, gehören in den Kern oder werden ausdrücklich eingebunden.
- **Aufträge gehören zum Motor.** Entschieden am 2026-10-01: Sie liegen nur im Plugin, Projekte ergänzen sie nicht. Projektspezifisches gehört in den Kontext, nicht in die Rollenbeschreibung. Sonst verhalten sich Rollen je Projekt unterschiedlich, und der Coach kann nicht mehr vergleichen. Verbesserungen laufen über die Lernschleife des Coaches und gelten dann für alle Projekte.
- Rollen mit nur einem Anlass (Entwickler, Tester) brauchen keine Teilung. Der Gewinn liegt bei Architekt, PO, Planer und Supervisor.

### Kontextprofil je Anlass

Wie viel Kontext eine Rolle bekommt, hängt am Anlass, nicht an der Rolle. Der Architekt braucht bei einer Schnittstellenprüfung etwas anderes als in der Wochenrunde. Jeder Anlass hat deshalb ein Profil, die Rolle legt nur die Obergrenze fest. Profil und Obergrenze stehen an einer einzigen Stelle, in `flow.py` neben den bestehenden Gates, je `rolle.anlass`.

Erster Vorschlag, Werte zur Diskussion:

| Rolle, Anlass | Module der Aufgabe | direkte Nachbarn | Karte | Obergrenze für Nachholen |
| --- | --- | --- | --- | --- |
| Entwickler, Tester, Reviewer | innen + schnittstelle | schnittstelle | nein | Nachbarn innen |
| Planer, Schneiden | innen + schnittstelle | innen + schnittstelle | ja | alles |
| Planer, Neuschnitt | wie Schneiden, plus ein Ring | | ja | alles |
| Architekt, `bewertung` und `kontext` | innen + schnittstelle | innen + schnittstelle | ja | alles |
| Architekt, `strukturfrage` | wie oben, plus ein Ring | | ja | alles |
| Architekt, `wochenrunde` | keine | keine | ja, plus Pflegeliste | alles |
| PO | keine | keine | ja | Schnittstellen |
| Supervisor | keine | keine | nein | keine, er liest keinen Code |
| Compliance, Auditor, Coach | Prüfrollen ohne Grenze, sie bewerten gerade, ob Kontext wirkt | | | |

Ein Projekt kann die Werte in `.keel/config.yaml` überschreiben. Ein Projekt mit einem einzigen Modul braucht keine Werte.

### Wer vergibt die Module einer Aufgabe

- **Auf Ebene des Plans.** In frühen Phasen (Problemstellung, Bewertung, Abnahmetests) gibt es noch keine `dateien`. Die betroffenen Module werden deshalb im Plan festgelegt: Der PO nennt sie bei der Problemstellung, der Architekt bestätigt oder korrigiert sie bei der Bewertung.
- **Auf Ebene der Aufgabe** leitet der Core die Module aus `dateien` ab. Der Planer ergänzt nur Querschnittsthemen wie `auth`, die man an Pfaden nicht erkennt.
- **Reparaturen** haben `dateien: []` und Vorrang. Sie bekommen `architektur.md` und keinen Modulkontext. Der Grenzscan meldet bei ihnen nur und leitet nicht zum Architekten um.

### Karte und Übergangszeilen

- **Karte statt Gelände.** Planer und Architekt bekommen den ganzen Graphen als Karte: je Modul Name, ein Satz zum Zweck und die Kanten, ohne Inhalt. Die Karte wird aus der Konfiguration erzeugt und hat eine Größengrenze. Wird sie zu groß, ist der Graph zu fein geschnitten. Als Ergänzung ist eine automatisch erzeugte Karte im Stil der Repo-Map von Aider denkbar, die aus dem Code statt aus der Konfiguration kommt.
- **Übergangszeilen.** Der Planer schreibt im Plan zu jedem direkten Nachbarn der betroffenen Module eine Zeile: `Übergang zu <Modul>: berührt | nicht berührt, weil …`. Das Gate prüft, dass zu jedem Nachbarn eine Zeile da ist. Aus Weitsicht wird so ein prüfbares Artefakt, und Architekt und Reviewer sehen, wo sie hinschauen müssen.
- Ob eine Zeile auch stimmt, prüft das Gate nicht. Das bewertet der Reviewer als Befund, und der Coach zählt, wie oft ein „nicht berührt“ später doch zu Problemen am Übergang führte.

### Wenn Kontext fehlt

- **Nachholen innerhalb der Obergrenze.** Über `kontext.py <modul> [--teil innen] --grund "<warum>"`. Der Grund ist Pflicht. Das Skript listet nur auf. Prüfen und Protokollieren übernimmt der Hook, der den Aufruf erkennt, denn nur er kennt Agent-ID, Rolle und Anlass.
- **Melden über die Obergrenze hinaus.** Der Agent schreibt in die Übergabe `kontext_fehlt: <was>, weil …` und beendet sich mit diesem Status. Der Lead startet den Auftrag dann nach einer festen Regel in `flow.py` mit erweitertem Profil neu oder leitet ihn weiter. Dafür braucht es einen neuen Status in `flow.py` (Gates und nächster Schritt), im Ablauf des Vorhabens, im Monitor und in `system.md`.
- **Eskalation erweitert um einen Ring.** Fachliche Konflikte landen heute beim Planer (Neuschnitt nach Testeinspruch oder erschöpftem Budget) oder beim Architekten (Strukturfrage). Diese Anlässe bekommen automatisch das Profil der Beteiligten plus einen Ring im Graphen. Der Supervisor ist dafür nicht die richtige Stelle, er entscheidet, wie der Mensch entscheiden würde, und liest keinen Code.
- **Erweiterung entlang von Kanten.** Wer zu einem Modul nachholt, das im Graphen nicht mit der Aufgabe verbunden ist, erzeugt einen Befund: Entweder fehlt eine Kante, oder die Aufgabe ist falsch geschnitten. Eine fehlende Kante wird eine Aufgabe für den Architekten. So lernt das System bei jeder Eskalation, wo die Modulgrenzen wirklich verlaufen.
- Melden darf in den Kennzahlen nicht als Fehler zählen, sonst unterbleibt es.

## Technik und Durchsetzung

### Zusammensetzen

- Der Systemprompt eines Subagenten ist laut Doku von Claude Code immer der statische Inhalt seiner Datei unter `agents/`. Das ist der Rollenkern.
- Auftrag und Kontext kommen über den Hook `SubagentStart` mit `additionalContext`, höchstens 10.000 Zeichen. Die Verkabelung gibt es schon: `agent-gate.sh` legt vor dem Start Rolle und Bezug in `pending-<rolle>` ab, `agent-start.sh` bindet beides an die Agent-ID. Künftig legt das Gate auch den Anlass ab, und `agent-start.sh` ruft den Core auf, der Auftrag und Kontext zusammensetzt.
- Eingespielt werden der Auftragstext und die Liste der Kontextpfade, nicht die Inhalte. Kleine Pflichtdokumente können eingebettet werden, solange die Grenze hält.
- **Den Anlass leitet das Gate ab.** Bei PO, Architekt und Supervisor steht er heute in der ersten Zeile. Bei Planer, Tester und Entwickler ergibt er sich aus `Vorhaben:` oder `Aufgabe:` und dem Status. Das Gate ermittelt ihn aus dem Treffer in den bestehenden Regeln, statt eine neue Zeile zu verlangen.
- **Fail closed.** `SubagentStart` kann nicht blockieren. Scheitert das Zusammensetzen, liefe der Agent ohne Auftrag los. Deshalb prüft `agent-gate.sh` die Größe schon vor dem Start und lehnt dort ab. `agent-start.sh` schreibt nach Erfolg eine Marke `agent-<id>.kontext`, und `tool-gate.sh` lehnt jedes Werkzeug ab, solange sie fehlt.
- **Der Lead schreibt keinen Kontext in den Prompt.** Der Lead ist kein Subagent und wird nicht vom `tool-gate.sh` erfasst. Er könnte Inhalte als Prosa in den Prompt kopieren. Der Prompt an eine Rolle besteht deshalb nur aus den Kopfzeilen, die das Gate liest, und das Gate lehnt längere Prompts ab.
- **Ausweichweg:** `PreToolUse` mit `updatedInput` kann die Eingabe eines Werkzeugaufrufs ändern. Ob das beim Agent-Werkzeug auch für den Prompt gilt, ist nicht dokumentiert und müsste per Versuch geklärt werden.

### Leseregeln: protokollieren, nicht als Sicherheitsgrenze verkaufen

Eine harte Lesesperre auf `.keel/kontext/` ist nicht durchsetzbar. Der Ordner liegt im Repo, und `rg`, `grep -r`, `find -exec cat`, `git grep` oder ein Python-Einzeiler erreichen ihn, ohne dass der Pfad im Aufruf steht. Die Sperre für den Kennzahlen-Ordner funktioniert nur, weil der außerhalb des Repos liegt.

Deshalb:
- Je Agent liegt eine Erlaubnisliste als Datei unter `state_dir`, unabhängig davon, ob sein Bezug eine Aufgabe, ein Plan oder eine Wochenrunde ist. Die Referenz in `agent-<id>.ref` ist nur bei Entwickler, Tester und Reviewer eine Aufgabe.
- Direkte Zugriffe (`Read`, `Grep` und `Glob` mit Pfad unter `.keel/kontext/`) außerhalb der Liste werden zunächst protokolliert. Abgelehnt wird erst, wenn die Messung zeigt, dass die Profile stimmen.
- Der Coach wertet die Abweichungen aus. Ein Zugriff außerhalb der Liste ist ein Signal, dass ein Profil zu eng ist, oder dass ein Agent herumliest.
- `log.sh` protokolliert schon heute jeden Lesezugriff. Darauf baut das auf.

### Grenzen prüft der Projekt-Lint

Der Entwickler bemerkt nicht immer, dass er eine Modulgrenze berührt, zum Beispiel wenn Blogposts direkt auf Interna von Profil zugreift. Dann ändert sich kein Dokument, und niemand wird ausgelöst. Das ist der gefährliche Fall von stillem Drift, weil Entwickler und Reviewer nur einen Ausschnitt sehen.

`konzept.md` sieht Modulgrenzen schon als „Konvention als Code“ im Prüftor des Projekts vor. keel baut deshalb keinen eigenen Import-Parser, sondern übersetzt den Graphen in die Konfiguration eines bestehenden Werkzeugs und wertet nur dessen Ergebnis aus:
- JavaScript und TypeScript: dependency-cruiser, eslint-plugin-boundaries (deren Regel `no-private` entspricht genau der Trennung von innen und Schnittstelle) oder Nx-Tags.
- Python: import-linter.

Meldet der Lint einen Zugriff außerhalb der Schnittstelle oder eine Verbindung, die der Graph nicht kennt, wird der Architekt mit Anlass `kontext` ausgelöst.

Warnung aus der Praxis: Shopify hat die Privacy-Prüfung in Packwerk mit Version 3.0 entfernt, weil die Trennung von öffentlich und privat im Alltag mehr Reibung als Nutzen brachte. Die Grenzprüfung sollte deshalb erst nur melden und nicht blockieren.

## Pflege und Drift

Zwei Fragen werden getrennt. Ist der Kontext nach der Änderung noch richtig? Das ist Pflege. Fügt sich die Umsetzung in die Architektur ein? Das ist Architekturprüfung. Wer abnimmt, hängt nach fester Regel davon ab, was sich ändert:

| Was ändert sich | Wer pflegt | Wer nimmt ab |
| --- | --- | --- |
| `innen` eines Moduls der Aufgabe | Entwickler, als Teil der Aufgabe | Reviewer, im normalen Review |
| `schnittstelle` oder Kanten im Graphen | Entwickler schlägt vor (`## Kontextvorschlag`) | Architekt, Anlass `kontext` |
| Grenzverletzung laut Lint | | Architekt, Anlass `kontext` |
| Drift, die niemand gemeldet hat | | Architekt, Wochenrunde |

- **Innen.** Ändert eine Aufgabe Code eines Moduls, verlangt das Gate in der Aufgabe `kontext: gepflegt | unverändert, weil …`. Der Reviewer vergleicht Diff und Kontext und bewertet die Begründung. Eine Floskel ist ein Befund.
- **Schnittstelle.** Sie ist ein Versprechen an andere Module, deshalb ändert der Entwickler sie nicht selbst. Ein offener Vorschlag blockiert die Aufgabe bis zur Abnahme, denn der Code setzt die neue Schnittstelle schon um. Lehnt der Architekt ab, ist die Aufgabe nicht fertig.
- **Drift.** Der Core zählt, wie oft der Code eines Moduls seit der letzten Kontextänderung geändert wurde. Module über einer Schwelle landen als Kandidaten auf der Pflegeliste, die der Architekt in der Wochenrunde sichtet.
- **Branches.** Entschieden am 2026-10-01: Moduldokumente reisen mit dem Code. Der Entwickler pflegt den inneren Teil auf dem Branch seines Vorhabens, und beides wird gemeinsam integriert. Ein früher integriertes Dokument würde etwas beschreiben, das es auf dem Basis-Branch noch nicht gibt. Konflikte unter `.keel/kontext/` sind dann seltene, echte Konflikte: Zwei Vorhaben ändern dasselbe Modul, und das soll sichtbar werden.
- **Erstbefüllung.** Bei der Bestandsaufnahme schreibt der Architekt Graph und erste Moduldokumente. Er braucht dafür Schreibrecht unter `.keel/kontext/`. Neue Module aus einem Epic legt er bei der Epic-Bewertung an.
- **Umbenennen und Aufteilen** von Modulen erledigt der Architekt in einem Schritt, samt Verweisen. Alte, abgeschlossene Aufgaben bleiben unverändert.

## Lernschleife und Messung

- **Ausgangsbasis vor der Einführung.** Aus `log.sh` und `events.jsonl` lässt sich heute schon auszählen, welche Dokumente Rollen lesen, wie viele Tokens eine Aufgabe kostet und wie oft Nacharbeit nötig ist. Ohne diese Basis lässt sich später nicht sagen, ob das Konzept wirkt.
- **Kennzahlen danach**: Nacharbeitsquote, Tokens je Aufgabe, Nachholen je Anlass, Meldungen `kontext_fehlt` je Anlass, Zugriffe außerhalb der Erlaubnisliste und Treffer des Grenz-Lints.
- **Messen je Anlass statt je Rolle.** Eine Rolle, die bei Bewertungen gut und in der Wochenrunde schwach ist, fällt heute im Durchschnitt nicht auf.
- **Der Coach schlägt Anpassungen vor**, wie bei den Schutzmaßnahmen: Wird ein optionales Dokument fast immer nachgeholt, wird es Pflicht. Bewirkt ein Pflichtdokument nie etwas, kommt es raus. Holt ein Anlass immer wieder dasselbe nach, ist sein Profil zu eng.

## Graph, Bestandsbild und Zielarchitektur

Der Graph ist mehr als eine Quelle für Kontext. Er ist die beste Ausgangslage für den Architekten, schlechte Architektur zu erkennen. Ein wilder Graph mit Zyklen, Gottmodulen und Abhängigkeiten kreuz und quer ist ein Alarmsignal. Heute kann keel das nicht erkennen und nicht gegensteuern, vor allem nicht in einem Bestandsprojekt.

### Was es heute gibt

Der Architekt hat den Anlass `bestandsaufnahme` (`/keel:architektur bestand`). Er liest die Codebasis und schreibt `architektur.md` als Ist-Zustand, fünf bis zehn Bestands-ADRs und einen Bericht mit Abweichungen. Dabei fehlen drei Dinge:
- Der Schritt ist optional. Ein Bestandsprojekt kann ohne ihn loslegen.
- Er beruht auf Lesen, nicht auf einem Graphen. Was der Architekt über Abhängigkeiten sagt, ist eine Einschätzung.
- Es gibt nur ein Ist, kein Soll. Der Architekt kann Abweichungen vom Bestand melden, aber auf kein Ziel hinarbeiten.

### Vorschlag: verpflichtender Einstieg für Bestandsprojekte

Bei `/keel:init` in einem Projekt mit Code kommt eine feste Folge. Bevor sie abgeschlossen ist, startet kein Vorhaben.

1. **Graph erzeugen, deterministisch.** `init` erkennt den Stack (zum Beispiel `package.json` oder `pyproject.toml`), wählt das passende Werkzeug (dependency-cruiser, import-linter, …) und erzeugt den Importgraphen. Dazu berechnet der Core Kennzahlen: Zyklen, Fan-in und Fan-out je Modul, Gottmodule (beides hoch), Instabilität nach Robert C. Martin, Dichte des Graphen. Der Architekt bekommt die Kennzahlen und eine verdichtete Karte, nicht den rohen Graphen, denn ein roher Graph eines großen Projekts sprengt jeden Kontext.
2. **Module vorschlagen, deterministisch vorbereitet.** Ein Clustering-Verfahren (etwa Community Detection nach Louvain) schlägt Gruppen vor, die eng miteinander und lose mit dem Rest verbunden sind. Der Vergleich mit der Ordnerstruktur ist selbst ein Befund: Decken sich Cluster und Ordner, ist die Struktur ehrlich. Weichen sie stark ab, lügen die Ordner.
3. **Architekt bewertet und legt die Module fest.** Er übernimmt, schneidet um oder verwirft die Vorschläge und schreibt Module mit Pfaden und Kanten in die Konfiguration.
4. **Werkzeuge festlegen.** Der Mensch nennt die Werkzeuge des Projekts (GitHub Issues, Linear, …). Das kann früh im Ablauf passieren, es hängt nicht vom Graphen ab. Erst mit dem Werkzeug-Katalog wirksam.
5. **Bestandsbild schreiben.** `architektur.md` beschreibt wie heute das Ist, jetzt mit Belegen aus dem Graphen.
6. **Zielarchitektur vorschlagen.** Erkennt der Architekt ein klares Muster, ist das Ziel meist das Muster ohne seine Verstöße. Erkennt er keins, schlägt er zwei oder drei Zielbilder mit Kosten vor. Die Entscheidung trifft der Mensch, so wie beim Zielbild des Produkts.

### Ist und Soll getrennt

- `architektur.md` bleibt das **Ist**: Regeln, die der Code einhält und gegen die der Reviewer prüft.
- Neu ist `zielarchitektur.md`, das **Soll**: welche Module es geben soll, welche Abhängigkeiten erlaubt sind, welches Muster gilt. Es wird unabhängig vom Bestand formuliert. Nur so kann der Architekt später Korrekturen vorschlagen und auf ein Ziel hinarbeiten, statt immer nur den Bestand zu bestätigen.
- Der Abstand von Ist zu Soll wird ein Migrationspfad: gebündelt als Epic oder als Pflegeaufgaben aus der Wochenrunde. Ob und wann daran gearbeitet wird, entscheidet der Mensch im Backlog.

### Wer ändert das Soll

Entschieden am 2026-10-01: Der Mensch entscheidet. Das Soll ist aber kein Denkmal. Ein Projekt ändert mit der Zeit seine Anforderungen, und dann kann ein Ziel, das einmal richtig war, falsch werden. Eine Rolle muss das erkennen und Vorschläge einbringen.

- **Der Architekt bewertet das Soll neu** (Anlass `soll-pruefung`) und schreibt eine Vorlage. Entschieden wird sie vom Menschen.
- **Auslöser, nach fester Regel:**
  - `zielbild.md` des Produkts hat sich geändert.
  - Ein Epic widerspricht bei der Epic-Bewertung dem Soll.
  - Die Ratsche zeigt, dass dieselbe Regel immer wieder als Ausnahme markiert oder umgangen wird. Das ist ein Zeichen, dass die Regel nicht zur Wirklichkeit passt.
  - Die Verstöße sinken über längere Zeit nicht, obwohl daran gearbeitet wird.
  - Regelmäßig, etwa einmal im Quartal, über die bestehende Fälligkeit (`due.py`), auch ohne Anlass.
- **Ein Soll wird nicht still angepasst.** Weder Architekt noch Supervisor ändern es selbst. So bleibt die Ratsche ein Maßstab und wird nicht zum Spiegel des Bestands.

### Auf das Ziel hinarbeiten: die Ratsche

Die Grenz-Linter können Regeln des Soll prüfen und bestehende Verstöße als bekannt markieren (dependency-cruiser hat dafür eine Datei für bekannte Verstöße, ähnlich Suppressions bei ESLint oder Ignores bei import-linter). Daraus wird eine Ratsche:
- **Keine neuen Verstöße.** Neuer Code muss das Soll einhalten. Das ist eine harte, deterministische Prüfung im Prüftor.
- **Alte Verstöße dürfen nur weniger werden.** Die Zahl der bekannten Verstöße wird je Integration verglichen und darf nicht steigen.
- **Der Trend ist die Kennzahl.** In der Wochenrunde vergleicht der Architekt die Kennzahlen des Graphen mit der Vorwoche. Wichtiger als ein absoluter Wert ist, ob Zyklen, Gottmodule und Verstöße gegen das Soll mehr oder weniger werden.

Damit wird „auf das Zielbild hinarbeiten“ messbar, ohne dass ein Umbau auf einen Schlag nötig ist.

### Ist und Soll im Review

Entschieden am 2026-10-01:
- **Neuer Code folgt dem Soll.** Neue Dateien und neue Abhängigkeiten müssen dem Soll entsprechen, die Ratsche prüft das hart.
- **Änderungen an bestehenden Stellen dürfen dem Ist folgen**, solange sie keinen neuen Verstoß einführen. Niemand muss nebenbei umbauen.

### Selbstheilung des Altbestands

Der Altbestand soll aber nicht ewig still neben dem Soll liegen. Wie stark das System von sich aus auf das Soll hinarbeitet, legt das Projekt in der Konfiguration fest:

```yaml
selbstheilung:
  stufe: vorschlagen        # aus | vorschlagen | mitnehmen | umbauen
  mitnehmen_max_zeilen: 30  # Obergrenze für einen Fund, der nebenbei behoben werden darf
  umbau_anteil_prozent: 20  # nur bei umbauen: Anteil der Aufgaben, der in den Umbau gehen darf
```

| Stufe | Was passiert |
| --- | --- |
| `aus` | Nur die Ratsche. Es kommen keine neuen Verstöße dazu, die alten bleiben. |
| `vorschlagen` | Der Architekt sammelt in der Wochenrunde Verstöße gegen das Soll und schlägt die leicht zu behebenden als Backlog-Einträge vor. Du entscheidest, was eingeplant wird. Standard. |
| `mitnehmen` | Wie `vorschlagen`. Zusätzlich behebt der Entwickler leicht zu behebende Verstöße in Dateien, die seine Aufgabe ohnehin ändert, in einem eigenen Commit. |
| `umbauen` | Wie `mitnehmen`. Zusätzlich plant der Architekt aktiv Umbauaufgaben auf das Soll hin, bis zum festgelegten Anteil. Strukturänderungen bleiben eine Entscheidung des Menschen. |

**Die schwierige Grenze: Was ist leicht zu beheben?** Das darf kein Urteil des Agenten sein, sonst wird „nebenbei“ zum versteckten Umbau. Leicht zu beheben ist ein Verstoß nur, wenn alle vier Bedingungen gelten, und die prüft der Core:
1. Er liegt in einer Datei, die die Aufgabe ohnehin ändert.
2. Die Behebung ändert keine Schnittstelle und fügt keine Kante im Graphen hinzu. Sie entfernt nur die verletzende.
3. Sie bleibt unter `mitnehmen_max_zeilen`.
4. Die betroffene Stelle ist von Tests abgedeckt.

Alles andere wird kein Mitnehmen, sondern ein Vorschlag.

**Anschluss an Bestehendes.** Verstöße gegen das Soll laufen über die Pflegeliste aus System-ADR 0018: Der Architekt bündelt sie in der Wochenrunde und routet sie als Pflegeaufgaben, begrenzt durch `pflege.max_aufgaben_pro_runde`. Mitgenommene Behebungen stehen in einem eigenen Commit, damit das Review als Delta sauber bleibt. Der Trend der Verstöße zeigt, ob die gewählte Stufe reicht.

### Kopplung jenseits von Importen

Ein Importgraph zeigt nur statische Abhängigkeiten. Kopplung über gemeinsame Tabellen, Events, HTTP oder Konfiguration sieht er nicht. Ein Teil davon lässt sich aber ebenfalls deterministisch erkennen und als zusätzliche Kanten in den Graphen bringen. Recherche vom 2026-10-01, in der Reihenfolge des Nutzens:

1. **Datenbank über das ORM** (leichtester Einstieg). Die Metadaten des ORM sagen, welche Datei welche Tabelle definiert, zum Beispiel `getDMMF` bei Prisma, `getTableConfig` bei Drizzle, `_meta.db_table` bei Django oder `__tablename__` bei SQLAlchemy. Der vorhandene Importgraph sagt dann, welche Module dieses Modell nutzen. Daraus entsteht eine Kante wie „blogposts und profil nutzen die Tabelle users“. Schreiben und Lesen zu trennen, ist der nächste Schritt (über Aufrufe wie `create` und `update`).
2. **Gemeinsame Änderungen in der Git-Historie** (Change Coupling, wie bei code-maat und CodeScene). Dateien, die immer wieder zusammen geändert werden, sind gekoppelt, egal über welchen Kanal. Die Methode ist sprachunabhängig, die Formel einfach selbst zu bauen. Sie zeigt aber nur eine Korrelation. Sie taugt deshalb als Hinweis für den Architekten, nicht als Gate.
3. **SQL im Code.** Parser wie sqlglot oder libpg_query lesen Tabellennamen aus SQL-Texten. SQL, das erst zur Laufzeit zusammengesetzt wird, entgeht ihnen. Ergänzend ist eine Eigentümer-Datei je Tabelle möglich, nach dem Vorbild des Database Dictionary von GitLab (`db/docs/*.yml` mit Tabelle, Klassen und Bereich). Shopify geht weiter: Bei ihnen gehört jede Tabelle genau einer Komponente.
4. **Events und HTTP** nur, wo es Spezifikationen gibt. AsyncAPI liefert Sender und Empfänger je Kanal, OpenAPI und Pact liefern, wer wen aufruft. Ohne Spezifikation bleiben nur Suchmuster je Bibliothek (Semgrep, ast-grep) für Topics, die als festes Literal im Code stehen. Laufzeitdaten aus OpenTelemetry eignen sich erst bei mehreren Diensten.

Jede Kante trägt ihre Herkunft (Import, Tabelle, Historie, Spezifikation), damit der Architekt weiß, wie belastbar sie ist. Harte Prüfungen in der Ratsche gibt es nur für Import- und Tabellenkanten. Kanten aus der Historie sind Hinweise.

### Grenzen des Ansatzes

- Auch mit zusätzlichen Kanten bleibt Kopplung unsichtbar, die über dynamisches SQL, zur Laufzeit gebaute Topics, Konfiguration oder geteilte Annahmen läuft. Ein sauberer Graph beweist keine saubere Architektur.
- Kennzahlen sind Signale, keine Urteile. Manche Architekturen haben bewusst einen zentralen Kern mit hohem Fan-in. Die Bewertung bleibt beim Architekten, die Kennzahlen machen sie nur prüfbar.
- Für kleine Projekte muss die Folge kurz bleiben. „Ein Modul, Soll gleich Ist“ ist eine zulässige Antwort.
- In einem neuen Projekt ohne Code gibt es keinen Graphen. Dort wird nur das Soll festgelegt, und die Ratsche greift ab dem ersten Code.

### Welche Architektur eignet sich für Agenten?

Recherche vom 2026-10-01. Keine Architektur ist empirisch als besonders geeignet für Agenten belegt. Eine Studie, die den Erfolg von Agenten nach Aufbau des Repos vergleicht, wurde nicht gefunden. Eine Arbeit von 2026 findet sogar, dass die Suchstrategie des Agenten mehr ausmacht als der Aufbau des Repos. Praxisberichte stimmen aber in vier Punkten überein: Änderungen bleiben lokal, Schnittstellen sind schmal und ausdrücklich, Regeln werden maschinell geprüft, Indirektion gibt es nur, wo sie echte Arbeit leistet.

**Was hilft, mit Stärke der Belege:**
- **Feature-Schnitt statt Schichten** (vertikale Slices). Alles zu einem Feature liegt an einer Stelle, der Agent lädt weniger Fremdes. Bisher nur Argumentation, keine Messung.
- **Tiefe Module nach Ousterhout.** Schmale Schnittstelle, viel Verhalten dahinter, eine klare Grenze für Tests. Das passt genau zur Trennung von `innen` und `schnittstelle`. Ebenfalls nur Meinung.
- **Mechanisch geprüfte Abhängigkeitsrichtung.** OpenAI beschreibt für Codex eine feste Richtung der Schichten, durchgesetzt von Lintern, deren Fehlermeldungen gleich einen Hinweis zur Korrektur enthalten. Dazu kommen Grenzen für Dateigrößen und eine kurze AGENTS.md als Inhaltsverzeichnis. Das ist ein Herstellerbericht.
- **Starke Typisierung.** Laut einer von GitHub zitierten Studie sind 94 % der Kompilierfehler in Code von Sprachmodellen Typfehler. Das ist der stärkste Beleg in dieser Liste.
- **Gesunder Code.** Eine Studie (FORGE 2026) findet bei Code mit guten Werten für Code-Gesundheit 15 bis 30 % weniger Fehler beim Refactoring durch Sprachmodelle, allerdings an Übungscode, nicht an Firmenprojekten.
- **Monorepo.** Der Agent sieht beide Seiten einer Schnittstelle, Änderungen über Grenzen hinweg sind atomar. Die Belege sind Anekdoten.
- **Regeln je Verzeichnis statt global** (Stripe), dazu deterministische Prüfungen.

**Was schadet:**
- **Indirektion aus Gewohnheit.** In einem einzelnen, wenig aussagekräftigen Versuch brauchte eine hexagonale Architektur ohne echte Grenze rund 70 % mehr Tokens und mehr als doppelt so viele Dateien für dieselbe Aufgabe.
- **Features, die über viele Ordner verstreut sind.**
- **Aufgeblähte oder von Sprachmodellen erzeugte Kontextdateien.** Siehe Stand der Technik.
- **Viele Repos** ohne organisatorischen Grund.

**Folgerung für das Soll.** Wenn der Architekt kein klares Muster im Bestand findet, schlägt er als Standard vor:
- einen modularen Monolithen im Monorepo,
- Module als Feature-Schnitte, innen flach,
- je Modul eine schmale öffentliche Schnittstelle mit Tests an dieser Grenze,
- Ports und Adapter nur an echten Außengrenzen (Datenbank, externe Dienste), nicht als Schablone für jedes Modul,
- Typisierung, wo die Sprache sie erlaubt.

Für die Ratsche folgt daraus: Fehlermeldungen der Linter enthalten einen Hinweis zur Korrektur, und neben Modulgrenzen können Dateigrößen und Werte für Code-Gesundheit Teil der Ratsche werden. Da öffentliche Vergleichsdaten fehlen, sammelt keel eigene: Dateien und Tokens je Aufgabe, Grenzverletzungen und Nacharbeit, jeweils je Architekturmuster der Projekte.

## Werkzeug-Katalog (später)

Neben dem Modulkontext gibt es eine zweite Achse: Werkzeuge wie GitHub Issues oder Linear. Werkzeugkontext hängt an der Rolle, nicht an der Aufgabe. Der PO braucht Linear immer, der Entwickler nie.

- Das Plugin liefert einen Katalog `katalog/werkzeuge/<name>/` mit einem Regeldokument, optional einem Skill für die Bedienung und einer Deklaration, welche Rollen das Werkzeug nutzen dürfen und woran man einen Aufruf erkennt (Befehlsmuster, Namen von MCP-Werkzeugen).
- `/keel:init` fragt die Werkzeuge ab, trägt sie in `.keel/config.yaml` ein und kopiert die Einträge nach `.keel/kontext/werkzeuge/`. Projekte können Eigenheiten ergänzen. Eine Version im Frontmatter zeigt, wenn der Katalog neuer ist, dann kommt der Eintrag auf die Pflegeliste.
- Aus der Deklaration ergeben sich Kontext und Erlaubnis. Kontext wegzulassen schränkt nämlich nichts ein: Ein Agent ohne Linear-Dokument kann das Werkzeug trotzdem aufrufen. Durchsetzung über `guard.sh` (Befehle) und `tool-gate.sh` (MCP-Werkzeuge), zunächst nur protokollierend.

Die Modul-Achse wird so gebaut, dass diese Achse später ohne Umbau dazukommt: dasselbe Frontmatter, derselbe Auflöser, dieselben Hooks.

## Einführung in Stufen

| Stufe | Inhalt | Voraussetzung, um weiterzugehen |
| --- | --- | --- |
Es gibt zwei Stränge. Der Architektur-Strang hat einen eigenen Nutzen, unabhängig davon, ob sich Modulkontext bewährt, und er liefert die Module, die der Kontext-Strang braucht.

**Architektur-Strang**

| Stufe | Inhalt | Voraussetzung, um weiterzugehen |
| --- | --- | --- |
| A1 | Graph und Kennzahlen deterministisch erzeugen, Bestandsaufnahme darauf stützen | Kennzahlen entsprechen der Einschätzung des Architekten in Testprojekten |
| A2 | Module vorschlagen, `zielarchitektur.md`, Einstieg für Bestandsprojekte verpflichtend | Mensch nimmt Soll an, Folge bleibt für kleine Projekte kurz |
| A3 | Ratsche im Prüftor, Trend der Kennzahlen in der Wochenrunde | Verstöße sinken über Wochen, wenig Fehlalarme |

**Kontext-Strang**

| Stufe | Inhalt | Voraussetzung, um weiterzugehen |
| --- | --- | --- |
| K0 | Ausgangsbasis messen, nichts ändern | Basis für Nacharbeit, Tokens und Lesezugriffe liegt vor |
| K1 | Rollenkern und Auftrag je Anlass für Architekt und PO, eingespielt über `SubagentStart`, mit Fail-closed | Tokens je Aufruf sinken, Qualität der Bewertungen bleibt gleich |
| K2 | Moduldokumente innen und Schnittstelle (Module aus A2), Module im Plan, Zugriffe nur protokolliert | Projekte mit mehreren Modulen zeigen weniger Nacharbeit oder weniger Tokens |
| K3 | Karte, Übergangszeilen, Grenzen über Projekt-Lint (nur meldend), `kontext_fehlt` | Lint und Übergangszeilen finden echte Probleme, wenig Fehlalarme |
| K4 | Ablehnen statt protokollieren, wo die Messung es trägt | |
| K5 | Werkzeug-Katalog | |

K0, K1 und A1 hängen nicht voneinander ab und können parallel laufen. K2 braucht A2. Jede Stufe wird ein eigenes System-ADR mit Hypothese, wie ADR 0016 und 0018.

## Stand der Technik

Wir sind nicht die Ersten. Eine Recherche am 2026-10-01 hat Folgendes ergeben. Die Quellen sind verlinkt, Studien wurden nicht einzeln nachgeprüft.

**Kontext nach Pfad zuordnen ist verbreitet, nach Aufgabe und Rolle nicht.**
- Cursor (`.mdc`-Regeln mit `globs`), Claude Code (`.claude/rules/` mit `paths`), GitHub Copilot (`*.instructions.md` mit `applyTo`), Kiro (Steering mit `fileMatch`) und Windsurf ordnen Regeln deterministisch zu, aber nach der Datei, die gerade berührt wird, nicht nach Aufgabe oder Rolle. Viele bieten zusätzlich einen Modus, in dem das Modell anhand einer Beschreibung selbst entscheidet. Laut Doku von Claude Code ist CLAUDE.md Kontext und keine Durchsetzung, zum Blockieren soll man Hooks nehmen.
- AGENTS.md kennt nur „die nächstgelegene Datei gilt“, ohne Frontmatter.
- Cline Memory Bank lädt pauschal alles. Aider erzeugt eine Repo-Map aus dem Code mit festem Token-Budget, das kommt unserer Karte am nächsten.
- Am nächsten an „geben statt holen“ ist BMAD: Der Scrum Master schreibt den relevanten Ausschnitt der Architektur in eine eigenständige Story-Datei. Die Auswahl trifft dort aber ein Modell, kein Regelwerk.
- „Codified Context“ (arXiv 2602.20478) leitet über Tabellen anhand geänderter Dateien an Fach-Agenten weiter. Die Tabellen stehen aber als Prosa im Prompt und werden nicht von Code ausgewertet. Der Erfahrungsbericht nennt veraltete Spezifikationen als Ursache stiller Fehler.

**Grenzprüfung gibt es fertig.** import-linter, dependency-cruiser, eslint-plugin-boundaries, Nx und Packwerk prüfen Modulgrenzen. Erste Projekte nutzen solche Regeln als Gate für Agenten (etwa lintel). Ein Werkzeug, das denselben Graphen für Kontext und Lint nutzt, wurde nicht gefunden.

**Die Evidenz zu Kontextdateien ist gemischt.**
- Anthropic empfiehlt die kleinstmögliche Menge an Tokens mit hohem Signal. Chroma zeigt an 18 Modellen, dass die Leistung mit wachsender Eingabe abnimmt und Ablenker schaden. Das stützt den engen Zuschnitt.
- Eine Studie der ETH (arXiv 2602.11988) findet bei Kontextdateien keine höhere Erfolgsquote, aber über 20 % Mehrkosten, und Agenten befolgen sie wörtlich. Eine andere (arXiv 2607.27250) findet, dass die Kontextstrategie die Korrektheit nicht messbar bewegt. Das ist das stärkste Argument für Stufe 0: messen, bevor gebaut wird.
- Cognition warnt, dass isolierte Subagenten widersprüchliche implizite Entscheidungen treffen. Das ist ein Gegenargument gegen harte Abschottung und spricht für Karte, Übergangszeilen und die Entscheidungen in der Aufgaben-Datei, die keel schon hat.
- „Ask or Assume?“ (arXiv 2603.26233) meldet bei unterspezifizierten Aufgaben eine höhere Lösungsquote, wenn Agenten nachfragen. Das stützt `kontext_fehlt`.

**Was neu ist**: Zuordnung nach Aufgabe und Anlass statt nach berührter Datei, Reichweite über einen Modulgraphen, ein Graph als gemeinsame Quelle für Kontext und Lint, und eine Lernschleife über protokolliertes Nachholen.

**Was wir übernehmen statt bauen**: das Glob-Format für Pfade, bestehende Grenz-Linter, gegebenenfalls eine automatisch erzeugte Karte.

## Risiken

- **Veraltete Moduldokumente.** Das größte Risiko. Ein veraltetes Pflichtdokument, das zuverlässig geladen wird, ist schlimmer als keins. „Codified Context“ berichtet genau das. Gegenmittel: Pflege als Teil der Aufgabe, Driftzählung, Wochenrunde.
- **Kein messbarer Nutzen.** Die Studienlage ist gemischt. Gegenmittel: Stufe 0 und Abbruchkriterien je Stufe.
- **Aufwand für kleine Projekte.** Gegenmittel: Ein Modul ist der Standard, und alles darüber kommt nur mit Befund.
- **Neue Gates blockieren den Ablauf.** Fehlerhafte Übergangszeilen, unbekannte Module oder Größengrenzen würden die Korridore `blockierte_uebergaben_prozent` und `budget_verstoesse` auslösen, wegen des Konzepts und nicht wegen schlechter Arbeit. Gegenmittel: erst protokollieren.
- **Floskeln in Pflichtfeldern.** „unverändert, weil …“ und Übergangszeilen lassen sich mit Boilerplate erfüllen. Gegenmittel: Der Reviewer bewertet die Begründung, der Coach misst, wie oft eine Begründung später nicht stimmte.
- **Isolation führt zu widersprüchlichen Entscheidungen** (Einwand von Cognition). Gegenmittel: Schnittstellen der Nachbarn sind immer dabei, ebenso die Entscheidungen früherer Aufgaben.
- **Moduldokumente laufen zwischen Branches auseinander.** Andere Vorhaben sehen bis zur Integration den alten Stand. Das ist gewollt, weil Dokument und Code zusammen reisen. Konflikte unter `.keel/kontext/` zeigen, dass zwei Vorhaben dasselbe Modul ändern.
- **Die Trennung von innen und Schnittstelle erzeugt Reibung** (Erfahrung von Packwerk). Gegenmittel: Grenz-Lint erst nur meldend.
- **Die Unschärfe wandert zur Zuordnung der Module.** Abhilfe schafft die Ableitung aus Pfaden, ganz verschwindet das Problem nicht.
- **Zurückgelassene Pending-Dateien.** Scheitert ein Start nach dem Gate, aber vor `SubagentStart`, bleibt eine veraltete Pending-Datei liegen. Die Zuordnung ist nicht atomar. Mit dem Anlass in der Datei ändert sich außerdem ihr Format.

## Offene Fragen

- ~~Wie werden Moduldokumente zwischen Branches synchron gehalten?~~ Entschieden, siehe „Pflege und Drift“.
- Ab welcher Schwelle wird ein Modul zum Kandidaten für die Pflegeliste: eine feste Zahl oder eine Zahl relativ zur Größe des Moduls?
- ~~Dürfen Projekte die Aufträge je Anlass ergänzen?~~ Entschieden: nein, siehe „Rollenkern und Auftrag je Anlass“.
- Ist ein Katalogeintrag für ein Werkzeug Kontext, Skill oder beides? Und wie kommen Verbesserungen aus Projekten zurück in den Katalog?
- Lässt sich der Prompt eines Subagenten über `updatedInput` ändern? Das ist per Versuch zu klären, falls `SubagentStart` nicht reicht.
- Wie sieht die Ausgangsbasis in Stufe K0 genau aus, und welche Projekte liefern genug Daten?
- Welche Kennzahlen des Graphen sind aussagekräftig genug für einen Alarm, und ab welchen Werten? Lieber Trend als Schwelle?
- ~~Wie geht der Reviewer mit Code um, der dem Ist folgt, aber dem Soll widerspricht?~~ Entschieden, siehe „Ist und Soll im Review“ und „Selbstheilung des Altbestands“.
- ~~Wer darf das Soll ändern?~~ Entschieden, siehe „Wer ändert das Soll“.

## Verlauf

Entscheidungen und Korrekturen aus dem Brainstorming am 2026-10-01:

- Kontext liegt zentral und projektspezifisch unter `.keel/kontext/`, nicht neben dem Code.
- Den Kontext gibt die übergeordnete Instanz mit, der Agent holt ihn sich nicht selbst.
- Werkzeuge bilden eine zweite Achse, die an der Rolle hängt. Der Katalog kommt später.
- Die Reichweite folgt einem Modulgraphen, und jedes Modul hat zwei Teile. Planer und Architekt bekommen die Karte.
- Die Feinheit wächst mit dem Projekt, Standardwerte können je Projekt überschrieben werden.
- Pflege: innen nimmt der Reviewer ab, die Schnittstelle der Architekt, Drift sammelt die Wochenrunde. `architektur.md` bleibt globaler Rahmen.
- Der Rollenkern bleibt in der Agentendefinition, Auftrag und Kontext je Anlass werden eingespielt. Die Reichweite hängt am Anlass, nicht an der Rolle.
- Der Graph dient auch dem Erkennen schlechter Architektur. Bestandsprojekte bekommen einen verpflichtenden Einstieg: Graph, Module, Werkzeuge, Bestandsbild, Zielarchitektur. Ist und Soll werden getrennt, und eine Ratsche arbeitet auf das Soll hin.
- Das Soll ändert nur der Mensch. Der Architekt bewertet es bei festen Auslösern und regelmäßig neu und schlägt vor.
- Neuer Code folgt dem Soll, bestehende Stellen dürfen dem Ist folgen. Wie stark der Altbestand geheilt wird, regelt eine Konfiguration mit vier Stufen.
- Moduldokumente werden mit ihrem Code integriert.
- Aufträge je Anlass gehören zum Motor, Projekte ergänzen sie nicht.
- Korrektur nach der Prüfung: Die Lesesperre ist nicht durchsetzbar, deshalb wird zunächst protokolliert. Fachliche Eskalationen gehen an Planer und Architekt, nicht an den Supervisor. Grenzen prüft der Projekt-Lint statt eines eigenen Scans. Vor allem anderen kommt eine Messung.
