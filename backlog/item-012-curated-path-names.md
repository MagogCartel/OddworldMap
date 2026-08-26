# 12. Curated path names

**Status:** open — content pass · **Effort:** incremental curation · **Where:** anywhere, viewer data only

## What and why

The plumbing, the AO batch and all of AE are live. What remains is content, landing incrementally under the schema test's protection.

## Sketch

- **AO gaps (15 paths, no citable source yet):** all of Monsaic Lines (L1 P1/P2/P3/P5/P6 — the entrance, the chant gate, the nexus with the temple doors), Paramonia interiors (F1 P2/P5/P6/P7), Scrabania interiors (D1 P3/P4/P6/P8), Credits (C1 P1), the menu level (S1 P1). The list is derived rather than a count to trust: it is exactly the paths carrying neither a curated name in [annotations.json](../public/annotations.json) nor a disc `name` in `map_data_ao.json`, so recompute it instead of reading it.
- **AE follow-up (one path):** FeeCo `P3` is the level's only inferred name. Terminals 1, 2, 4 and 5 are each fixed by their own artwork, and the Slig Barracks terminal shows no number anywhere in its fifteen cameras, so `Terminal 3: Slig Barracks` stands by elimination. Downgrade it to `Slig Barracks Terminal` if that reading is ever contradicted.

## Findings

The sources used so far, credited in full in the [README](../README.md#credits--licensing): New 'n' Tasty chapter names (official), community walkthrough path names cross-checked against the map data's own TLV contents, and for AE the game's own zulag/tunnel/block/terminal signage read off the camera art.

Coverage, measured 2026-08-26: AO 41 of 74 paths curated, AE 114 of 117, and no AE path carries a disc `name` at all since the section split moved the thirteen ender labels out of it. Any older figure quoting AE at 0 curated predates both the AE batch and that split; read the shipped data rather than a written count.

## Shipped

**The plumbing, 2026-07-20.** [annotations.json](../public/annotations.json) as the hand-curated source — one file, both games keyed by id, levels as `{name, note?}` for off-map levels only — with [js/annotations.js](../public/js/annotations.js) owning the shape and the precedence. Schema tests cross-check every entry against the shipped map data: existence, canonical keys, trimmed.

**The precedence flipped during the work, and the buttons are what showed why.** `pathDisplayName` was written as a fallback — use the curated name only where the disc has none — and became a deliberate override, because Rupture Farms Return's four identical zulag buttons were the case that made "the disc's own label always wins" indefensible.

**It shipped alongside the off-map-destination fix**, which belongs to the same concern: a destination the map cannot follow — a missing level, or one of the 45 AE one-way doors, teleporters and wells with placeholder `P0` returns — used to offer a pointer cursor and a false "click to follow", and dumped you on the destination level's first path. Those lost the cursor and the promise, the click falls through to the screen list, and the tooltip says where the data points. Connection-arrow stubs still draw the raw `→ MI P0` labels deliberately: that is passive data display, not a claim you can go there.

Then the AO batch, and later all of AE.
