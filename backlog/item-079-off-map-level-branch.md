# 79. Retire the level annotations, keep the off-map clause

**Status:** open · **Effort:** small (viewer, schema, docs) · **Where:** anywhere, no disc · **Filed:** 2026-08-07, out of [7](item-007-ao-menu-level.md)

## What it is

Rendering `S1` took AO's count of destinations naming a level the map does not render from two to zero, and AE has none. Three things were left describing nothing in the shipped data: the tooltip's off-map clause in [js/interaction.js](../public/js/interaction.js), `levelInfo` in [js/annotations.js](../public/js/annotations.js), and `annotations.json`'s `levels` section, `{}` in both games, along with the schema rules policing it — a level entry must name a level *not* on the map, and may not be note-only.

## Decided: they are not the same question

Unreachable against the deployed data is not the same as dead, and measuring separates the three cleanly rather than leaving one verdict to cover them.

**The clause is reachable and stays.** Measured 2026-08-07 over a one-level dataset, the shape a `--levels` build emits into an empty output directory: two destinations name an absent level, `R1 P19` and `R1 P20`, both `PathTransition`s. Naming no partner, they are exactly the links `destTrusted` believes wherever they point, so the clause renders. That is a developer's tree rather than the site, but it is a tree anyone rebuilding a subset is standing in, and a fallback is what keeps it from offering a follow into nothing.

**The annotations half is dead and goes.** `levels` is empty in both games, `levelInfo` has no other caller, and a hand-curated file should not carry two rules about a section with nothing in it. The one entry it ever held moved to `S1 P1` when the level began rendering.

## Sketch

Delete the `levels` section, `levelInfo`, and the schema rules for both — together, since a half-removal leaves the schema policing a field no code reads. `sanitizeAnnotations` builds its output from a named set of keys, so `levels` comes out of that too or it is silently dropped rather than rejected. The tooltip keeps its clause and loses only the parenthetical name and the note line beneath it; both already render conditionally on `info`, so removing the lookup degrades it to `→ leads to LV Pn — not on the map` without a branch of its own.

## Watch out

This reverses the first commit of [37](item-037-per-path-notes.md), which existed to display a level note that had shipped unread. Nothing is lost: that note is on `S1 P1` now, where the place panel shows it.

[CLAUDE.md](../CLAUDE.md) records both halves as kept for data that could name an off-map level, which stops being true of the annotations half — that line wants editing in the same commit.

The measurement is the argument for keeping the clause, so it belongs in the commit message rather than only here; a later reader finding an unexercised fallback deserves to know a subset build exercises it.
