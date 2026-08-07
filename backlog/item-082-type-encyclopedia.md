# 82. Type encyclopedia cards

**Status:** open · **Effort:** medium (viewer) + incremental curation · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

The glossary ([17](item-017-field-glossary.md)) explains *fields*; nothing explains *types*. A visitor who meets a `ZBall`, a `SlapLock` or a `Greeter` on the map gets a name, a box and a pile of fields, and has to leave the site to learn what the thing is. One curated paragraph per type would turn the map into the reference its data already supports — and unlike the field glossary's long tail, the type list is finite (95 AO, 99 AE on the shipped maps, most shared).

## Sketch

- Content: a `types` tier alongside the existing glossary tiers (or a sibling `types.json`) — one plain-English paragraph per type name, game-agnostic where the type is shared, with the same one-JSON-line economics as [17](item-017-field-glossary.md).
- Surface: a card that opens from any object name — tooltip, screen list, Fields picker heading — carrying the curated paragraph, the type's field definitions (already in the glossary), its per-game count (derived live from the loaded data, never hand-written), and a "find all" link that seeds search with the type name.
- `data-tip` ([35](item-035-glossary-tooltips-touch.md)) is the one-string tooltip and stays that; a card with a link and a count needs a real surface — the screen list's panel pattern or a fifth `.overlay` dialog, whichever the entry points favour.

## Watch out

- Derived counts must stay derived: a hand-written "there are 152 mines" goes stale on the next rebuild, and the demo-path setting changes what a visitor would count. Say what the count covers.
- The curation bar is the same as the nicknames': describe what the shipped data and the games show, don't guess at engine internals.
