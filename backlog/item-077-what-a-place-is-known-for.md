# 77. What a place is known for

**Status:** open — the set is settled, the surface is not · **Effort:** small-medium (viewer + curation) · **Where:** anywhere, viewer data only · **Filed:** 2026-08-04 Brewery nickname review

## Why

A player who has just been chased through a room full of slogs, or who is standing next to a tear extractor, knows exactly where they are and has no idea which zulag it is. The map cannot answer that. Level and path buttons say `P10`, or `P10 — Zulag 10` with full names on, and a number is the one thing that player does not have.

The Brewery is the worst case and the reason this was noticed: fourteen zulags, numbered and nothing else, whose numbers are painted on boards the player has usually run past. But the problem is general. Necrum's tunnels, FeeCo's terminals and the Barracks' blocks are all numbered the same way.

A note is not the answer, and [37](item-037-per-path-notes.md) already established why in a different context: a note is a curiosity read after you arrive, reached through the place chip and a click. Four Brewery notes shipped in *Note what the fans call four of the Brewery's zulags* carrying exactly the words a lost player would search for, and every one of them is two clicks deep on a path you have to already be standing on.

## The set

The Oddworld Wiki's SoulStorm Brewery article names each zulag as a "sector". Nine of the fourteen describe something the shipped data confirms, three do not, and two were never assessed. Reviewed 2026-08-04 against `map_data_ae.json` and against the artwork in the viewer; every count below re-derives from the shipped data, so recompute rather than trusting the figure.

Holds up, by counting:

- **3 Industrial Machines** — 25 drills, more than any other area in the level.
- **6 Electrical Devices** — 11 electric walls, likewise.
- **4 Tear Gas** — 5 laughing gas, likewise.
- **7 Blind Mudokon** — 3 blind Mudokons, the only ones in the brewery. `blind` is a `Choice_short`, so it carries no entry in `enum_labels_ae.json` and a lookup keyed on the generated labels finds nothing; read the raw field.
- **2 and 11 Flying Sligs #1 / #2** — flying sligs stand on exactly two of the fourteen zulags, two on each. The pair is the claim, not the magnitude.
- **8 Slog Warehouse #2** — 4 slogs and 4 slog spawners, and slog spawners stand on only two zulags.
- **10 Slig High Security** — 9 sligs. It ties zulag 9, but zulag 9 is the wiki's own "Junior Executive Office #2" and was never competing for the name. The decompilation's demo table names the zulag 10 copy "Sligs" independently.
- **12 Tear Extractors #1** — 2 `TorturedMudokon`, and the artwork paints TEAR X-TRACTOR on the wall directly under the rig. First-hand signage, so this one is not the wiki's claim at all.

Does not hold up:

- **5 Slog Warehouse #1** — 3 slogs and no spawner, and the screens do not read as storage.
- **13 Junior Executive Office #3** — the Glukkon is really there, on the Final Secret Area half, so the original rejection was wrong on its stated ground. The room is another tear extractor floor rather than an office, which is what actually sinks the name.
- **14 Tear Extractors #2** — no `TorturedMudokon` anywhere on it.

Never assessed: **1** and **9**, both "Junior Executive Office". They are the two most Glukkon-heavy zulags in the level, at 2 and 4, which is suggestive and nothing more.

`TorturedMudokon` is what a tear extractor is stored as, which is the find that reopened the question: the original review concluded the extractor was scenery no object could speak to. The calibration is the path the game signs itself, `Zulag 4: Tear X-Tractor`, holding three of them.

## Why it is not a name

The four that shipped went into notes rather than names on the grounds that a board number and a fan nickname are claims by different authors, and only a note can attribute one. That reasoning does not survive contact with the file it was written for. `Zulag 9: Fleech Ledge` and `Brewery Terminal` are site coinages sitting in `name` with no attribution at all, and `Zulag 13: Final Secret Area` is a walkthrough's section title.

What survives is narrower and is the way through. The map is the author of "Fleech Ledge", so it owes nobody a citation. If the map writes its own verified description of the same fact, it is the same kind of thing and owes nothing either. The wiki's contribution was noticing which feature characterises a place, and a characterisation confirmed against the shipped data is the map's claim to make. That also makes it testable, which a borrowed nickname could never be: "zulag 3 holds more drills than any other area" is assertable in `tests/unit/`, and "zulag 3 is Industrial Machines" is not.

Folding it into `name` was considered and does not work. Every colon name in the Brewery marks a sub-path of a zulag that spans more than one path — zulag 4 is P18 and P19, zulag 9 is P17 and P21, zulag 13 is P15 and P20, and those three are the only multi-path zulags, with all eleven single-path zulags carrying a bare name. `Zulag 10: Slig High Security` would assert a division of zulag 10 that does not exist, and would be the only colon in the level meaning something other than the other three.

## Where it could show

Undecided, and deliberately left so. Three surfaces were discussed and none is ruled out:

- **The path button face, with full names on.** The only surface that answers the scanning case the item exists for, and the only one carrying layout risk. Check the longest line the level would produce before committing to it.
- **The button tooltip.** Free, and currently wasted: measured 2026-08-04, 20 of 21 Brewery path buttons and 7 of 11 Mudanchee Vault ones have a `title` that repeats the button's own label verbatim once full names are on. Only the entry points and the ender halves add anything. Desktop only, so it cannot be the sole home.
- **Search**, through [60](item-060-search-place-names.md). Measured 2026-08-04 in Chrome against the dev server: `tear`, `x-tractor`, `high security` and `monsaic` return nothing, while `slig`, `drill`, `electric wall` and `blind` all hit. The gap is precisely between the player's vocabulary and the developers': a tear extractor is stored as `TorturedMudokon`, and "high security" is not an object at all. Note that `slig` returns 819 object hits, so a place row is only useful in the separate Places group that [60](item-060-search-place-names.md) already specifies, never mixed in.

One trap worth naming: searching `zulag 2` today returns **Zulag 12's** status boards, because `LCDStatusBoard` carries a `zulag_number` field and 12 contains a 2. The one place-shaped query that works today is wrong.

## Discipline

[37](item-037-per-path-notes.md) was retired rather than completed because an open item asking for more notes invites forced ones. The same trap is worse here, because fourteen numbered zulags in a column look like fourteen blanks to fill. Five of the fourteen already have nothing to say. A phrase arrives when a place genuinely has something you would recognise it by.

## What the working notes held

The reasoning behind roughly 160 curated path names lived in an uncommitted scratch file while this was being decided. Most of it has a destination already: per-path evidence has become notes, and the nickname list has become this item. Three things had none, and were confirmed on 2026-08-04 to appear in no committed file:

- **The three-tier source hierarchy** the AE names were derived under: the camera art first (the recurring status board prints the local number, "EMPLOYEES THIS ZULAG n", "EMPLOYEES THIS TUNNEL n", "VOLUNTEERS THIS BLOCK n", "ATTENDANTS THIS TERMINAL n", alongside the arch signs and FeeCo's departures wall map), then the decompilation's own tables, then a walkthrough checked section by section against the object census.
- **The naming conventions**: a second or third stretch of one named place takes a roman numeral (`Mudomo Vaults II`), a distinct sub-place inside one takes a colon (`Tunnel 1: Secret Area`), a demo copy is `[Demo] <the path it copies>: <the demo's title in the decomp table>`, and a level's own name is never repeated in its path names.
- **Which levels have no first-hand numbers at all**: Bonewerkz prints its company logo where the board's number belongs, and both vaults carry no signage, so their names rest on the walkthrough alone.

Those three are material for [12](item-012-curated-path-names.md) rather than for this item — that is where the remaining naming work is — but they are recorded here so the file they came from can go.

## Findings

**The level graph is twelve links, not thirteen.** The working notes listed thirteen inter-level crossings, one more than `tests/unit/map-data.test.js` pins. The extra one is Necrum Vaults to FeeCo Terminal 1, and it is real in the game and absent from the data: `NE P3`'s express well carries `FD P1 C1` on its unused side with well 0, and FeeCo P1 has no well in C1, its two sitting in C08 and C09 pairing with each other. The crossing happens in a cutscene, the way the Mines' P1 to P2 transition does, and FeeCo P1 has the `AbeStart` that confirms it. Twelve is the followable graph and the test is right; CLAUDE.md calling it "the games' whole level graph" is a shade strong.

## Ships with

A README bullet, and a `changelog.json` entry of its own. Nothing to supersede: the entry added by *Note what the fans call four of the Brewery's zulags* was taken out again by *Stop giving note batches their own changelog entries*, which is where a batch of notes stopped earning one.
