---
nummer: 0025
titel: Freigaben für keels eigene Befehle in unbeaufsichtigten Läufen
status: Accepted
datum: 2026-10-05
entscheider: Ich
supersedes:
hypothese: Ein unbeaufsichtigter Lauf (claude -p, keel-run.sh) in einem frischen Projekt kommt ohne angesammelte Freigaben durch Tagesstart, Rollen, Prüftor und Integration; kein erlaubter Befehl hat im Probelauf etwas außerhalb des Projekts verändert
---

# 0025: Freigaben für keels eigene Befehle in unbeaufsichtigten Läufen

## Kontext

Der erste `/keel:start` im neuen Beispielprojekt endete beim ersten Befehl: `due.py` brauchte eine Freigabe, und ohne Menschen lehnt Claude Code in `-p`-Läufen jede Rückfrage ab. keel brachte nie Allow-Regeln für Bash mit; im alten Beispielprojekt hatten sich Freigaben aus interaktiven Sessions angesammelt. `keel-run.sh` läuft genauso mit `--permission-mode acceptEdits` und wäre an derselben Stelle stehen geblieben. Statische Regeln in `.claude/settings.json` vergleichen Präfixe und kennen den Pfad zum Plugin nicht, der sich zwischen Installation und `--plugin-dir` unterscheidet.

## Entscheidung

Ein Schritt `allow` im Dispatcher (`PreToolUse` auf `Bash`, System-ADR 0022) gibt `permissionDecision: allow` zurück, wenn jeder Teil des Befehls auf einer festen Liste steht:

- keels Skripte und Kommandozeile aus dem Ordner dieses Plugins, auch als `${CLAUDE_PLUGIN_ROOT}` geschrieben;
- `test.command`, `test.acceptance` und die Präfixe in `freigaben.befehle` (`.keel/config.yaml`, Standard leer, vom Menschen gepflegt);
- git mit festen Unterbefehlen ohne Force: lesen, `add`, `commit` (ohne `--amend`, `--no-verify`), `switch`, `merge`, `mv`, `tag`, `pull --ff-only`, `push` (nicht auf `main`, kein Löschen, kein `+`), `branch` nur zum Auflisten; `-C` nur ins Projekt;
- `cd` ins Projekt und `date`.

Befehlsersetzung, andere Variablen als `$PWD` und `${CLAUDE_PLUGIN_ROOT}`, Heredocs und Umleitungen in Dateien werden nie erlaubt. Alles andere bekommt keine Antwort und läuft durch die normale Freigabe. Der Schritt antwortet nur in einem Projekt mit `.keel/config.yaml`.

Ablehnungen gehen vor: Guard, Werkzeug-Gate und alle anderen Gates des Ereignisses verweigern weiter, und Deny- und Ask-Regeln der Settings wertet Claude Code laut Hook-Doku unabhängig von der Antwort des Hooks aus. Fällt der Schritt aus, ist das ein `hook_error` und keine Erlaubnis.

## Verworfen

- **Statische Allow-Regeln per `init.sh`:** Präfixvergleich mit wechselndem Plugin-Pfad, und `git push` lässt sich so nicht von `git push origin main` trennen.
- **`--permission-mode bypassPermissions` für unbeaufsichtigte Läufe:** schützt nur noch über Deny-Regeln und Guard und gibt auch Befehle frei, die keel nie braucht.

## Folgen

- Ein Entwickler, der Tests einzeln laufen lassen will, braucht dafür ein Präfix in `freigaben.befehle`; sonst nur `test.command`.
- Neue Befehle in Skills und Rollen brauchen einen Eintrag in `services/hooks/allow.py` und einen Vertragstest, sonst halten sie unbeaufsichtigte Läufe an.
