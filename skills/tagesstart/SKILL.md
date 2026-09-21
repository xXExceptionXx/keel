---
name: tagesstart
description: Startet den Arbeitstag. Startcheck der Umgebung, bei Rot eine Reparaturaufgabe, dann Übergabenotiz des Vortags in Kurzform, Inbox und die Vorhaben mit Status. Aufruf mit /keel:tagesstart.
---

Du bist der Lead im keel-System und beginnst den Tag frisch. Du lädst nur aus Dateien.

**0. Basis-Branch.** Lies `git.base_branch` aus `.keel/config.yaml` (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" "$PWD" git.base_branch main`) und wechsle dorthin: `git switch <base>`, dann `git pull --ff-only`, falls ein Remote existiert. Der Tag beginnt auf der Basis; Vorhaben-Branches wechselt `/keel:vorhaben` selbst. `main` fasst der Lead nie an, außer es ist die Basis.

**1. Startcheck.** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gate.sh" "$PWD" startcheck`. Ist er rot, führe den Ablauf aus der Skill `keel:reparatur` aus, bevor du weitermachst. Bleibt er danach rot, brich ab und melde das in drei Zeilen.

**2. Vortag.** Lies das Frontmatter der neuesten Übergabenotiz unter `.keel/work/handoff/` und gib aus ihrem Body nur die Zeilen **Offen** und **Probleme** wieder. Gibt es keine, sag das.

**3. Prüfbefunde routen.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/route_findings.py" "$PWD"`. Jeder Befund des jüngsten Prüfberichts ohne ID wird mechanisch zu einem Backlog-Element mit Herkunft Audit („wird Aufgabe“) oder zu einer Vorlage („wird Vorlage“); die ID steht danach im Bericht. Du urteilst nicht über die Befunde, der Vermerk des Auditors entscheidet. Gab es etwas zu routen: `git add .keel && git commit -m "Route audit findings <Datum>"`. Nenne in der Ausgabe die Zahl und die IDs; der Mensch entscheidet im Backlog, ob aus „vorgeschlagen“ ein „bereit“ wird.

**4. Inbox.** Führe den Ablauf aus der Skill `keel:inbox` aus.

**5. Vorhaben.** Liste alle Pläne unter `.keel/work/plans/` mit `vorhaben`, `titel`, `status`, nur aus Frontmatter, dazu `git branch --list '<feature_prefix>*'`. Pläne mit Status `abgenommen` werden mit `/keel:vorhaben <name>` integriert; nenne sie zuerst.

**6. Empfehlung.** Genau ein Satz: welches Vorhaben als Nächstes mit `/keel:vorhaben <name>` fortgesetzt oder gestartet werden sollte, in dieser Reihenfolge: `in-arbeit` vor `geplant` vor `abnahmetests-bereit` vor `problemstellung`. Ist nichts offen, sag, dass das Backlog dran ist.

Keine Erzählung, keine Wiederholung der Übergabenotiz in voller Länge.
