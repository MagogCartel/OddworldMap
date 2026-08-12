# 82. Type encyclopedia cards

**Status:** shipped 2026-08-12 · **Effort:** medium (viewer) + incremental curation · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

The glossary ([17](item-017-field-glossary.md)) explains *fields*; nothing explains *types*. A visitor who meets a `ZBall`, a `SlapLock` or a `Greeter` on the map gets a name, a box and a pile of fields, and has to leave the site to learn what the thing is. One curated paragraph per type would turn the map into the reference its data already supports — and unlike the field glossary's long tail, the type list is finite (95 AO, 99 AE on the shipped maps, most shared).

## Sketch

- Content: a `types` tier alongside the existing glossary tiers (or a sibling `types.json`) — one plain-English paragraph per type name, game-agnostic where the type is shared, with the same one-JSON-line economics as [17](item-017-field-glossary.md).
- Surface: a card that opens from any object name — tooltip, screen list, Fields picker heading — carrying the curated paragraph, the type's field definitions (already in the glossary), its per-game count (derived live from the loaded data, never hand-written), and a "find all" link that seeds search with the type name.
- `data-tip` ([35](item-035-glossary-tooltips-touch.md)) is the one-string tooltip and stays that; a card with a link and a count needs a real surface — the screen list's panel pattern or a fifth `.overlay` dialog, whichever the entry points favour.

## Watch out

- Derived counts must stay derived: a hand-written "there are 152 mines" goes stale on the next rebuild, and the demo-path setting changes what a visitor would count. Say what the count covers.
- The curation bar is the same as the nicknames': describe what the shipped data and the games show, don't guess at engine internals.

## Shipped

- The content landed as a sibling `glossary_types.json` rather than a glossary tier: one paragraph per type name under a `types` section, the first sentence doubling as the summary — the anchortip line-break model applied to JSON. Style, prose shape and coverage are pinned in `tests/unit/typeinfo.test.js`; the keys are exactly the shipped type set (139 across both games, re-measured 2026-08-12 — 95 AO, 99 AE, 55 shared — which the coverage assertion reproduces on every run).
- The surface is a fifth `.overlay` dialog, not the screen list's panel pattern: the card's openers live map-side and sidebar-side both, and on narrow the one-sheet-at-a-time rule would close the screen list underneath, where a modal covers it and Escape returns to it.
- The sketch's tooltip entry point resolved the way [19](item-019-field-picker-from-tooltip.md) did: a hover tooltip cannot host a control, so it carries the summary sentence as plain prose and the card opens from the ⓘ at each screen-list row's edge and beside each Fields-picker heading (the ⚙'s treatment, generalised into a shared class).
- Counts are `census()` per game, derived at open time, with the numbers panel's demo footnote saying what the listed count leaves out; the field definitions are the glossary's, in the current game's terms; find-all seeds search with the type name and opens the drawer on narrow.
- The paragraphs were written from a whole-decomp research pass (both games' sources, master and beta), each engine claim traced to its read site and every count or placement stated in prose re-derived from the shipped data before it shipped. Where the decomp's own labels mislead (a Slig's *listening* state, ScrabNoFall, ElumStart), the entry says what the engine does and lets the label stand beside it.
