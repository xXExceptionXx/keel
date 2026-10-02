# Sicherheit

## Was die Schutzregeln leisten

keels Hooks (`hooks/guard.sh`, `hooks/tool-gate.sh` und die Gates) sind ein Netz gegen Versehen: Sie halten Rollen in ihren Grenzen, schützen die Tests des Testers und sperren offensichtlich destruktive Befehle. Sie sind **keine Sandbox**. Ein Modell, das gezielt nach Umgehungen sucht, oder ein Mensch mit Shell-Zugriff kommt an ihnen vorbei. Wer keel in einem Projekt mit sensiblen Daten oder Zugängen einsetzt, braucht zusätzlich die Mittel von Claude Code selbst (Berechtigungsmodus, Deny-Regeln, Sandbox) und eine Umgebung, in der ein Fehlgriff begrenzt bleibt.

## Bekannte Lücken

Bekannte Umgehungen stehen offen in `docs/kern-befunde.md`, Abschnitt 3 „Schutzregeln, die sich umgehen lassen“, mit Fundstelle und Stand der Behebung. Was dort als offen markiert ist, gilt als bekannt.

## Eine Lücke melden

Neue Lücken bitte nicht als öffentliches Issue, sondern über GitHubs „Report a vulnerability“ im Reiter Security dieses Repos (Private vulnerability reporting). Hilfreich sind die keel-Version aus `.claude-plugin/plugin.json`, die Claude-Code-Version und ein Aufruf, der die Regel umgeht.
