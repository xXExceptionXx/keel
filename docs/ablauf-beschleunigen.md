# Ablauf beschleunigen: der Core erledigt das Feststehende

2026-10-01 · Konzeptentwurf, noch keine Entscheidung und kein ADR. Schwesterdokument zu `kontext-scope.md`.

## Kurzfassung

Agenten verbrauchen viel Zeit und Kontext für Schritte, deren Ergebnis von vornherein feststeht: Status lesen und setzen, Konfiguration nachschlagen, Git-Befehle zusammensetzen, sich im Dateibaum orientieren, lange Ausgaben von Werkzeugen lesen. Diese Schritte unterscheiden sich nur in ihren Argumenten. Sie gehören in den Core, nicht in das Urteil eines Modells.

Der Grundsatz: **Was feststeht, erledigt der Core. Was ein Urteil braucht, erledigt der Agent.** Der Agent bekommt Fakten und Befehle mit klarer Wirkung, statt sie sich selbst zu erarbeiten.

Voraussetzung ist ein sauber aufgebauter Core mit einem einzigen Einstiegspunkt und klarer Ordnerstruktur. Sonst wird aus vielen kleinen Beschleunigungen ein unwartbares Sammelsurium von Skripten.

## Ausgangsbasis

Ausgezählt am 2026-10-01 aus dem Hook-Protokoll des Beispielprojekts (`~/.keel-metrics/<projekt>/hooks.jsonl`, rund 2300 Werkzeugaufrufe). Das ist ein einziges Beispielprojekt, also ein Hinweis, kein Beweis.

| Was | Aufrufe | Wer |
| --- | --- | --- |
| `frontmatter.py` (get, set, dump) | rund 260 | davon 220 der Lead, der Rest Tester, Entwickler, Reviewer |
| `config.py`, `briefing_needed.py`, `gate.sh` | rund 80 | fast nur der Lead |
| Git (`add`, `switch`, `status`, `log`, `diff`, `branch`) | rund 120 | fast nur der Lead |
| Orientierung (`ls`, `cat`, `grep`, `find`) | rund 300 | alle Rollen, `ls` allein rund 140 |
| `Read` | 431 | Tester 144, Reviewer 91, Planer 67, Entwickler 66 |
| Testlauf (`test.sh`) und Typprüfung (`tsc`) | 91 | Entwickler, Tester, Reviewer |

Werkzeugaufrufe nach Art: Bash 662, Read 431, Write 77, Edit 68, Agent 58.

Beobachtungen:
- **Der größte Posten ist die Buchhaltung des Leads.** Er arbeitet die Ablaufregeln mit Einzelbefehlen ab, obwohl sie deterministisch sind und zum Teil schon in `flow.py` stehen. Die Ablaufbeschreibung in `skills/vorhaben/SKILL.md` hat rund 1900 Wörter Prosa, die der Lead bei jedem Lauf liest und auslegt.
- **Orientierung kostet mehr als Suche.** Ein einzelner `grep` ist billig. Teuer ist, dass Agenten erst herausfinden müssen, wo etwas liegt und in welchem Zustand es ist.
- **Ein Vorbild gibt es schon.** `gate.sh` führt die Tests aus, legt die volle Ausgabe im Log ab und gibt eine Zeile aus, bei Rot zusätzlich die letzten 20 Zeilen. Genau dieses Muster fehlt an anderen Stellen.

Nebenbefund: Zwei Zeilen im Hook-Protokoll sind ineinander geschrieben, vermutlich durch gleichzeitiges Schreiben mehrerer Hooks. Das ist als eigene Aufgabe angelegt. Für saubere Kennzahlen muss es behoben sein.

## Grundsätze

1. **Was feststeht, erledigt der Core.** Ein Schritt, dessen Ergebnis sich aus Zustand, Konfiguration und Regeln ergibt, wird ein Befehl. Der Agent führt keine Befehlsfolge aus, die immer gleich ist.
2. **Fakten vor Urteilen.** Was sich messen oder ausrechnen lässt (Status, Testergebnis, Diff, Dateibaum, Kennzahlen), ermittelt der Core vorab und gibt es mit. Der Agent beginnt mit dem Urteil, nicht mit dem Erkunden.
3. **Kurze Ausgaben, volles Log.** Jeder Befehl gibt bei Erfolg eine Zeile aus, bei Fehlern das Nötige zur Behebung. Die vollständige Ausgabe liegt im Log, mit Pfad in der Meldung.
4. **Fehlermeldungen sagen, was zu tun ist.** Wie bei den Lintern von OpenAI für Codex: Eine Meldung nennt das Problem und den nächsten Schritt, nicht nur den Exit-Code.
5. **Kein Käfig.** Scheitert ein Befehl in einem Sonderfall, darf der Agent auf rohe Werkzeuge zurückgreifen. Ein Wrapper, der im Sonderfall nicht weiterhilft, kostet mehr, als er spart. Rückgriffe werden protokolliert, damit der Coach sieht, wo ein Befehl fehlt oder zu eng ist.
6. **Nur kapseln, was häufig ist.** Jeder Befehl ist Code, der gepflegt werden muss. Gekapselt wird, was die Messung als häufig zeigt, nicht alles, was möglich ist.

## Ansätze, nach Hebelwirkung

### 1. Ein Befehl für den nächsten Schritt

`keel next` liest den Zustand aller laufenden Vorhaben, wendet die Ablaufregeln an und gibt genau eine Anweisung zurück: welche Rolle mit welchem Anlass und welchen Kopfzeilen als Nächstes startet, oder dass ein Mensch gebraucht wird und warum. `keel done <ref>` nimmt das Ergebnis eines Rollenlaufs entgegen, prüft die Übergabe, setzt die Status, committet `.keel/` und gibt den nächsten Schritt aus.

Der Lead wird damit dünn: `next` aufrufen, Agent starten, `done` aufrufen. Das ersetzt den Großteil der rund 340 Buchhaltungsaufrufe, verkürzt die Ablaufbeschreibung in `skills/vorhaben/SKILL.md` auf wenige Absätze und senkt Fehler, weil der Lead die Regeln nicht mehr auslegt.

Das passt zum Kontextkonzept: Derselbe Core, der Rollenkern, Auftrag und Kontext zusammensetzt, setzt auch den Schritt zusammen. `next` liefert die Kopfzeilen, das Gate prüft sie, der Start-Hook spielt Auftrag und Kontext ein.

Was beim Lead bleibt: Agenten starten (das kann nur er) und Ausnahmen, für die es keine Regel gibt. Die meldet `next` ausdrücklich als „braucht Entscheidung“.

### 2. Werkzeug-Abläufe als feste Befehle

Git zuerst, weil es am häufigsten ist:
- `keel git start <vorhaben>`: Basis aktualisieren, Prüftor auf der Basis, Branch nach Konvention anlegen oder wechseln.
- `keel git commit <ref>`: Commit nach Konvention (englische Nachricht, `Keel-Task`-Trailer), danach `.keel/` nachcommitten.
- `keel git integrate <vorhaben>`: der ganze Schritt 5 aus `vorhaben/SKILL.md`, heute ein Absatz mit rund 15 Befehlen: Basis holen, Prüftor, Merge, Abnahmetests in die Regression verschieben, Prüftor, Status setzen, Branch aufräumen.
- `keel git discard <ref>`: Code-Änderungen einer Aufgabe verwerfen, `.keel/` behalten (heute `git restore` und `git clean` mit Ausschluss).

Konventionen wie Basis-Branch, Präfixe und Sprache stehen schon in `.keel/config.yaml` und werden dort gelesen, nicht vom Agenten zusammengesetzt. Dasselbe Muster gilt später für Issues, Linear und andere Werkzeuge aus dem Werkzeug-Katalog im Kontextkonzept.

### 3. Fakten vorab ermitteln

Bevor eine Rolle startet, ermittelt der Core, was sie sonst selbst erkunden würde, und gibt es im Auftrag mit:
- **Reviewer:** Ergebnis von Tests, Linter und Typprüfung, Diff-Statistik, geänderte Dateien mit Modul, Treffer des Grenz-Lints, Ergebnis des Compliance-Scans.
- **Entwickler:** Verzeichnisbaum der Modulpfade seiner Aufgabe, Ausgangszustand der Tests, Entscheidungen der vorigen Aufgaben.
- **Tester:** Liste der Abnahmetests mit Status, vorhandene Testdateien des Moduls, Ort für Tests aus `architektur.md`.
- **Planer:** Karte des Modulgraphen, Dateien je Modul.

Das ersetzt einen Großteil der rund 300 Aufrufe zur Orientierung. Grenze: die 10.000 Zeichen von `SubagentStart`. Fakten werden deshalb verdichtet. Was nicht passt, liegt als Datei unter `state_dir` und wird im Auftrag verlinkt.

### 4. Kurze Ausgaben von Werkzeugen

Das Muster von `gate.sh` wird zur Regel für alle Werkzeuge, die Agenten aufrufen: Testläufe, Typprüfung, Linter, Builds. Bei Erfolg eine Zeile. Bei Fehlern nur die fehlschlagenden Tests oder Fehlerstellen mit den ersten Zeilen der Meldung, nicht das ganze Log. Der Filter je Werkzeug ist eine kleine, testbare Funktion. Gemessen an Tokens ist das wahrscheinlich der zweitgrößte Hebel nach Ansatz 1.

### 5. Prüfungen automatisch nach jeder Änderung

Ein Hook nach `Edit` und `Write` lässt Formatter und Typprüfung auf der geänderten Datei laufen und gibt nur Fehler zurück. Der Agent muss nicht daran denken, `tsc` aufzurufen, und Fehler fallen sofort auf statt erst im Prüftor. Die Befehle je Sprache stehen in der Konfiguration. Was zu langsam ist (ganzes Projekt typprüfen), bleibt im Prüftor.

### 6. Übergaben vorbefüllen

Der Core legt die Übergabe-Datei einer Rolle vor dem Start an: Frontmatter fertig, Abschnitte als leere Überschriften nach dem Format des Anlasses. Der Agent schreibt nur Inhalt. Das spart die rund 45 Aufrufe von `frontmatter.py` durch Rollen und vermeidet Formatfehler, die heute erst das Gate findet.

### 7. Symbolindex statt Suchversuchen

Ein einzelner `grep` ist billig, und das eingebaute Grep-Werkzeug begrenzt die Ausgabe schon. Ihn zu kapseln bringt wenig. Teuer sind Suchketten: Agenten suchen in drei Anläufen, wo etwas definiert ist und wer es nutzt. Ein Index aus ctags oder einem Language Server beantwortet das deterministisch: `keel where UserProfile` gibt Definition und Nutzer aus. Der Index wird vom Core aktuell gehalten und ist Teil des Graphen aus dem Kontextkonzept.

### 8. Modell je Anlass

Mechanische Anlässe (Übergabe prüfen, Testlauf auswerten, Reparatur einfacher Formatfehler) können auf einem schnelleren Modell laufen, Bewertungen und Schnitte auf dem stärkeren. keel kennt Modelle heute je Rolle. Je Anlass ist der nächste Schritt und passt zum Profil je Anlass im Kontextkonzept. Ob ein schnelleres Modell reicht, misst der Coach mit dem bestehenden Vergleich je Modell.

### 9. Der Coach findet neue Kandidaten

Die Ansätze oben stammen aus einer einmaligen Auszählung. Damit das kein Einmaleffekt bleibt, wird das Finden neuer Kandidaten Teil der Lernschleife. Das passt zur Rolle des Coaches: Er ist die einzige Rolle mit Zugriff auf die Kennzahlen, und „Rückbau ist ein Vorschlag wie Einbau“ gilt für Befehle genauso wie für Schutzmaßnahmen.

- **Der Core findet Muster, der Coach bewertet sie.** Ein Bericht (`keel report muster`) zählt deterministisch aus dem Hook-Protokoll: wiederkehrende Befehle und Befehlsfolgen, normalisiert auf ihre Form (Argumente werden zu Platzhaltern), je Rolle und Anlass, mit Häufigkeit und geschätzten Tokens der Ausgabe. Der Coach bekommt die Kandidaten über einer Schwelle, nicht das rohe Protokoll.
- **Drei Arten von Vorschlägen:**
  - **Neuer Befehl:** Eine Folge tritt in vielen Läufen gleich auf, etwa „Status lesen, Konfiguration lesen, Branch wechseln“.
  - **Befehl erweitern:** Agenten weichen von einem bestehenden Befehl auf rohe Werkzeuge aus. Das protokollierte Ausweichen zeigt, welcher Fall fehlt.
  - **Befehl zurückbauen:** Ein Befehl wird über mehrere Coach-Läufe nicht genutzt.
- **Vorschlag mit Hypothese, Entscheidung beim Menschen.** Wie jede Justierung des Motors: Der Coach schreibt eine Vorlage mit erwarteter Ersparnis („rund 40 Aufrufe je Vorhaben weniger“), und beim nächsten Lauf prüft er, ob sie eingetreten ist. Er baut den Befehl nicht selbst. Umsetzen ist ein Vorhaben im keel-Repo.

So wächst der Core entlang gemessener Muster, nicht entlang von Ideen. Das hält ihn klein.

## Aufbau des Core

Heute liegen unter `scripts/` 21 Dateien flach nebeneinander: Bibliotheken (`frontmatter.py`, `config.py`, `flow.py`), Befehle (`backlog.py`, `pflege.py`, `review.py`), Berichte (`lage.py`, `metrics.py`, `monitor.py`), Werkzeug-Wrapper (`gate.sh`, `compliance_scan.py`) und Einstiegspunkte (`keel.sh`, `init.sh`). Skills und Agenten rufen sie mit vollem Pfad auf, etwa `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/frontmatter.py" set …`. Für die Ansätze oben kämen zwei Dutzend Befehle dazu. Ohne Ordnung wird das unübersichtlich.

### Zielstruktur (Vorschlag)

```
bin/
  keel                  Einziger Einstiegspunkt: keel <befehl> [argumente]
core/                   Bibliothek ohne Seiteneffekte beim Import
  state.py              Zustand lesen und schreiben (Frontmatter, Pläne, Aufgaben)
  config.py             Konfiguration mit Standardwerten
  flow.py               Ablaufregeln, Gates, Profile je Anlass: die eine Quelle
  context.py            Rollenkern, Auftrag und Kontext zusammensetzen
  events.py             Kennzahlen und Protokoll schreiben, atomar
  output.py             Kurze Ausgaben, Fehlermeldungen mit nächstem Schritt
commands/               Ein Modul je Befehl, dünn, ruft core und tools
  next.py  done.py  git.py  gate.py  kontext.py  backlog.py  pflege.py  review.py ...
tools/                  Wrapper für fremde Werkzeuge, je Werkzeug eine Datei
  git.py  test.py  lint.py  typecheck.py  graph.py  symbols.py
  filters/              Ausgabefilter je Werkzeug, einzeln testbar
reports/                Lesende Auswertungen
  lage.py  metrics.py  models.py  due.py  monitor/
hooks/                  Dünne Shims: bash ruft keel hook <name>, keine Logik
auftraege/              Aufträge je Rolle und Anlass (aus dem Kontextkonzept)
tests/
  core/  commands/  tools/  hooks/  gate/
```

### Regeln für den Aufbau

- **Ein Einstiegspunkt.** Skills, Agenten und Hooks rufen nur `keel <befehl>` auf, nie ein Skript mit Pfad. Das macht Aufrufe kurz, Umbauten im Inneren unsichtbar und Protokolle auswertbar: Jeder Aufruf ist ein Befehlsname.
- **Schichten mit fester Richtung.** `commands` nutzt `core` und `tools`. `tools` nutzt `core`. `core` nutzt nichts davon. `reports` liest nur. `hooks` enthalten keine Logik. Das prüft ein Import-Linter im eigenen Prüftor, also dieselbe Ratsche, die keel Projekten empfiehlt.
- **Eine Quelle für Regeln.** Ablaufregeln, Gates und Profile stehen nur in `core/flow.py`. Befehle, Hooks und Monitor lesen von dort. Prosa in Skills beschreibt, ersetzt aber keine Regel.
- **Einheitliche Schnittstelle je Befehl.** Jeder Befehl hat `--help`, eine kurze Textausgabe für Agenten und `--json` für Maschinen. Exit-Codes sind einheitlich: 0 Erfolg, 1 fachlich abgelehnt (mit Grund und nächstem Schritt), 2 Fehler im System.
- **Nur Standardbibliothek.** Wie heute beim Monitor: Python ohne Pakete, damit das Plugin ohne Installation läuft. Fremde Werkzeuge (Linter, ctags) sind optional und werden über `tools/` erkannt.
- **Tests je Schicht.** `core` und Filter mit Unit-Tests, Befehle mit Fixture-Projekten wie heute `tests/gate/`, Hooks mit simulierten Payloads.
- **Protokoll eingebaut.** Jeder Befehl schreibt ein Ereignis mit Name, Rolle, Dauer und Ergebnis über `core/events.py`. Damit misst der Coach, welche Befehle genutzt werden und wo Agenten auf rohe Werkzeuge ausweichen.

### Umbau ohne Bruch

- Die alten Pfade unter `scripts/` bleiben als dünne Weiterleitungen auf `keel <befehl>`, bis kein Skill und kein Agent sie mehr nennt. `check_references.py` oder ein eigener Check meldet verbliebene Verweise.
- Der Umbau läuft Befehl für Befehl, zuerst die Bibliotheken nach `core/`, dann die häufigsten Befehle. Jeder Schritt hält das Prüftor grün.
- Die Gate-Tests unter `tests/gate/` sichern die Ablaufregeln während des Umbaus ab.

## Einführung in Stufen

| Stufe | Inhalt | Voraussetzung, um weiterzugehen |
| --- | --- | --- |
| B0 | Protokoll reparieren, Ausgangsbasis aus mehreren Läufen erheben (Aufrufe je Art und Rolle, Tokens je Aufgabe, Dauer je Vorhaben) | Basis liegt vor |
| B1 | Zielstruktur des Core und Einstiegspunkt `keel`, alte Pfade als Weiterleitung | Prüftor grün, keine Verhaltensänderung |
| B2 | `keel next` und `keel done`, Ablaufbeschreibung in `vorhaben/SKILL.md` verschlankt | Buchhaltungsaufrufe des Leads sinken deutlich, Gate-Tests grün |
| B3 | Ausgabefilter für Tests, Typprüfung, Linter; Git-Befehle | Tokens je Aufgabe sinken |
| B4 | Fakten vorab und vorbefüllte Übergaben, zusammen mit K1 aus dem Kontextkonzept | Orientierungsaufrufe sinken, Qualität bleibt gleich |
| B5 | Prüfung nach jeder Änderung, Symbolindex, Modell je Anlass | je einzeln gemessen |
| B6 | Musterbericht für den Coach, Vorschläge für neue, erweiterte und zurückgebaute Befehle | Vorschläge des Coaches treffen ihre Hypothese |

B1 ist Voraussetzung für alles Weitere, weil jeder neue Befehl sonst in die flache Struktur wächst. B0 und B1 hängen nicht voneinander ab. Der Musterbericht aus B6 baut auf denselben Auszählungen wie B0 auf und kann früh einfach beginnen. Jede Stufe wird ein eigenes System-ADR mit Hypothese.

## Risiken

- **Abstraktion, die nicht trägt.** Ein Befehl, der den Normalfall abdeckt, im Sonderfall aber scheitert, zwingt den Agenten zu Umwegen und kostet mehr als vorher. Gegenmittel: Rückgriff erlaubt und protokolliert, Befehle nur für häufige Fälle.
- **Der Lead verlernt den Ablauf.** Wenn `next` alles entscheidet, kann der Lead Ausnahmen schlechter einordnen. Gegenmittel: `next` begründet jede Anweisung in einer Zeile, und „braucht Entscheidung“ ist ein ausdrückliches Ergebnis.
- **Fakten vorab werden zu viel.** Wer alles vorab mitgibt, ist wieder beim aufgeblähten Kontext. Gegenmittel: dieselbe Größengrenze und dasselbe Profil je Anlass wie im Kontextkonzept.
- **Umbau bindet Zeit, ohne sichtbaren Nutzen.** B1 ändert kein Verhalten. Gegenmittel: B1 klein halten und direkt mit B2 verbinden, wo der Nutzen messbar ist.
- **Wartung.** Mehr Befehle sind mehr Code. Gegenmittel: Schichtregeln im eigenen Prüftor, Tests je Schicht, Rückbau ungenutzter Befehle auf Vorschlag des Coaches.
- **Geteilte Logik driftet.** Wenn Monitor, Hooks und Befehle Regeln je selbst auslegen, laufen sie auseinander. Gegenmittel: eine Quelle in `core/flow.py`, wie es mit der Tabelle aus System-ADR 0017 schon begonnen hat.

## Offene Fragen

- Wie viele Läufe und Projekte braucht die Ausgangsbasis, damit sie belastbar ist?
- Soll `keel next` mehrere Vorhaben gleichzeitig kennen, oder bleibt es bei einem Vorhaben je Session?
- Wie weit reichen die Git-Befehle: nur lokale Abläufe oder auch Push, PR und Aufräumen auf dem Remote?
- Welche Sprachen bekommen zuerst Ausgabefilter und Prüfung nach Änderung? Vermutlich TypeScript und Python, weil das Beispielprojekt TypeScript nutzt und keel selbst Python ist.
- Wird der Symbolindex mit ctags gebaut (einfach, grob) oder über einen Language Server (genau, schwerer einzurichten)?
- Wo liegt die Grenze zwischen „Fakten vorab“ und Kontext? Vermutlich: Fakten sind errechnet und gelten nur für diesen Lauf, Kontext ist gepflegt und gilt dauerhaft.
