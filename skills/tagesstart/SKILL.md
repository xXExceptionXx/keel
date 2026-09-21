---
name: tagesstart
description: Startet den Arbeitstag. Startcheck der Umgebung, bei Rot eine Reparaturaufgabe, dann Übergabenotiz des Vortags in Kurzform, Inbox und die Vorhaben mit Status. Aufruf mit /keel:tagesstart.
---

Du bist der Lead im keel-System und beginnst den Tag frisch. Du lädst nur aus Dateien.

**1. Startcheck.** `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gate.sh" "$PWD" startcheck`. Ist er rot, führe den Ablauf aus der Skill `keel:reparatur` aus, bevor du weitermachst. Bleibt er danach rot, brich ab und melde das in drei Zeilen.

**2. Vortag.** Lies das Frontmatter der neuesten Übergabenotiz unter `.keel/work/handoff/` und gib aus ihrem Body nur die Zeilen **Offen** und **Probleme** wieder. Gibt es keine, sag das.

**3. Inbox.** Führe den Ablauf aus der Skill `keel:inbox` aus.

**4. Vorhaben.** Liste alle Pläne unter `.keel/work/plans/` mit `vorhaben`, `titel`, `status`, nur aus Frontmatter.

**5. Empfehlung.** Genau ein Satz: welches Vorhaben als Nächstes mit `/keel:vorhaben <name>` fortgesetzt oder gestartet werden sollte, in dieser Reihenfolge: `in-arbeit` vor `geplant` vor `abnahmetests-bereit` vor `problemstellung`. Ist nichts offen, sag, dass das Backlog dran ist.

Keine Erzählung, keine Wiederholung der Übergabenotiz in voller Länge.
