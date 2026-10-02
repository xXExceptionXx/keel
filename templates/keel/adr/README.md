# Architecture Decision Records

Eine Datei pro Entscheidung, fortlaufend nummeriert: `0001-kurzer-titel.md`. Neue ADRs legt `adr.py neu <projekt> <slug>` an (Plugin-Skript): auf dem Basis-Branch gleich mit der nächsten Nummer, auf einem Feature-Branch als Entwurf `entwurf-<slug>.md` mit `nummer: offen`. Die Nummer vergibt `adr.py number` bei der Integration und zieht alle Verweise unter `.keel/` nach; so nehmen zwei Branches nie dieselbe Nummer (System-ADR 0021). Vorlage: `0000-vorlage.md`.

`entscheider` ist immer die Stufe, die entschieden hat: leer bzw. `offen` bei _Proposed_, `PO`, `Supervisor` oder `Mensch`. Eine Rolle schreibt nur ihre eigene Stufe; ein Hook lehnt das Ende einer Rolle ab, die ein ADR auf fremder Stufe anlegt oder ändert.

Status: _Proposed_ → _Accepted_ oder _Accepted (delegiert)_ → später ggf. _Superseded by 00XX_.

Eine Umkehrung ändert nie das alte ADR. Es entsteht ein neues mit _Supersedes 00XX_. Der Index aktiver ADRs steht in `.keel/CLAUDE.md`.
