# 17. Field glossary

**Status:** open — content curation · **Effort:** incremental; each entry is one JSON line · **Where:** anywhere, viewer data only

## What and why

Architecture, wiring and visuals are live. What remains is **content** — curating meanings for more of the field names, which mostly needs game knowledge. Coverage as of 2026-07-31 is 44 entries against 451 distinct field names in the shipped data (both counts recomputable from [glossary.json](../public/glossary.json) and the `fields` archives in `map_data_{ao,ae}.json`); the fields objects show by default are nearly all covered, the picker-only long tail is not.

## Sketch

Add entries to [glossary.json](../public/glossary.json) in the tier that fits:

- `byField` — a global by name, for a field that means the same wherever it appears (e.g. `scale`).
- `byGameType` — keyed by the field's decomp game type (e.g. `Path_Slig::StartState`), so every object sharing that type shares the meaning (the group); the key is the same one `enum_labels` uses, findable in `field_types_{ao,ae}.json`.
- `byType` — `"ObjectType.field"`, for a meaning specific to one object type (wins over the group and the global).

The value list is automatic (from `enum_labels`/`TRANSFORM`), so an entry is just the prose. A schema test cross-checks every key against the shipped data.

## Decided

The three tiers, rather than the original flat "field name → meaning" sketch, which missed that the same name means different things per object (`start_state` on a Door is not `start_state` on a Slig).

## Findings

**The original sketch asked for a togglable panel and got per-field definitions instead.** It was filed as "a user-facing legend explaining what decoded tooltip fields mean" — a `?`-style button opening a panel, or per-field hover-defs as an alternative. The panel lost: a legend is a second place to look, and the question "what does this field mean" is always asked while looking at the field. So the definition went onto the field name itself, and there is no legend.

The floating hover tooltip cannot host a per-field hover, so the definitions live on the surfaces that hold still — the Fields picker and the screen list.

## Shipped

**Architecture and wiring, 2026-07-25.** [glossary.json](../public/glossary.json), hand-curated and game-agnostic, plus [js/glossary.js](../public/js/glossary.js) — `sanitizeGlossary` / `setGlossary` / `glossaryProse`, a leaf — resolving a field's meaning through the three tiers. `fieldHelp(game, type, field)` in [js/fields.js](../public/js/fields.js) composes the prose with the field's full value list, so an entry only ever has to carry the prose. Wired at boot beside the other sidecars, with a schema test pinning every key to the shipped data.

Seeded with exactly three entries, one per tier — `scale`, `Path_Slig::StartState`, `Mudokon.state` — because the content needs game knowledge and inventing it would have been worse than leaving it thin.

**Surfaced first as a native `title`** with a dotted underline, which was the right cheap start and the wrong end state: a `title` says nothing on touch, so the underline promised an explanation a phone could not collect. [35](item-035-glossary-tooltips-touch.md) replaced it with a real tooltip and then generalised the mechanism to any element carrying `data-tip`.
