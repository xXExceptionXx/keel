---
nummer: 0027
titel: keel-Rollen ändern Dateien mit Edit und Write, nicht über Bash
status: Accepted
datum: 2026-10-05
entscheider: Ich
supersedes:
hypothese: Im nächsten Vorhaben-Lauf kommt keine fehlende Freigabe mehr von einem Heredoc oder Inline-Skript einer Rolle, und keine Rolle braucht mehr als einen Versuch, bis sie zu Edit oder Write wechselt
---

# 0027: keel-Rollen ändern Dateien mit Edit und Write, nicht über Bash

## Kontext

Im zweiten Vorhaben-Lauf des Beispielprojekts kam gut ein Drittel der fehlenden Freigaben daher, dass Rollen Dateien über Bash änderten: `cat >> plan.md <<'EOF'`, `python3 - <<'EOF'` mit `str.replace`. Der Allow-Schritt (System-ADR 0025) erlaubt das zu Recht nicht. In einem unbeaufsichtigten Lauf erfährt die Rolle davon aber nur über eine stille Ablehnung und probiert oft mehrmals, bevor sie zu Edit oder Write wechselt.

## Entscheidung

Das Werkzeug-Gate lehnt bei keel-Rollen Bash-Befehle ab, die Dateien schreiben: Heredoc, Umleitung in eine Datei (nicht `/dev/null`, nicht in einen anderen Strom), `tee`, `sed -i`, `perl -i`, `python3 -`/`-c`, `node -e`. Die Begründung nennt Read, Edit und Write. Die Erkennung beachtet Anführungszeichen: Ein `>` in einer Commit-Nachricht oder einem grep-Muster ist Text. Der Lead und die Sessions des Menschen sind nicht betroffen.

## Verworfen

- **Nur die Rollentexte ergänzen.** Eine Regel in Prosa hält nicht, das zeigte der Lauf; das Gate sagt es beim ersten Versuch.
- **Auch den Lead einschränken.** Der Lead integriert und committet; seine Bash-Nutzung ist anders, und in interaktiven Sessions entscheidet der Mensch.

## Folgen

- Eine Rolle, die eine generierte Datei braucht (etwa eine Testausgabe), schreibt sie mit Write aus dem Ergebnis, nicht mit `> datei`.
