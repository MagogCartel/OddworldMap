# 75. A schema layout override can go stale unnoticed

**Status:** shipped 2026-08-06 · **Effort:** small (builder) · **Where:** anywhere — the schema cache is committed, no disc · **Filed:** 2026-08-01 review, triaged 2026-08-02

## What and why

`_FIELD_TYPE_OVERRIDES` is guarded: `write_field_types` raises *stale field-type override* when an entry names a field the schema no longer carries, so an override the decomp has since made unnecessary fails the build instead of quietly outliving its reason. Its sibling `_SCHEMA_LAYOUT_OVERRIDES` is applied by a bare `schema[tid] = layout` with no check of any kind, so an entry naming a type id the game does not have, or one the parser has since learned to derive on its own, stays in the table until somebody happens to look at it.

Both tables exist to correct the decomp, and [CLAUDE.md](../CLAUDE.md)'s standing rule is that such a correction is temporary — fixed upstream and re-pinned. A guard is what makes "temporary" mechanical rather than aspirational. The pattern has already played out once, in the good direction: the ContinueZone entry was retired the day the parser learned below-base names (*Read a field the decomp names below the payload base*, `f308557`) — but only because that commit's author was looking at the table. A redundant entry nobody is looking at stays.

## Sketch

Two checks where the override is applied, both cheap:

- the tid is a type id the game actually has, read from `tlv_names` rather than from the parsed schema;
- the override still *differs* from what the parser produced, which is what turns redundancy into a failure instead of a silence.

## Watch out

The second check is the one that needs care, and AO's `RingCancel` is why. Its override is an empty layout marking a genuinely field-less type, and the parser emits no key for that tid at all — so `schema.get(tid)` is absent rather than empty, and the two are correctly different. A guard that treated "the parser said nothing" and "the override says nothing" as the same thing would fire on the one entry the table currently holds.

## Verify

Add a bogus entry for a type id that does not exist and confirm the build fails by name; add a duplicate of what the parser already produces and confirm the same. Then re-emit both sidecars into a scratch directory and byte-compare against the committed ones, since nothing here is supposed to change any output.

## Shipped

The first check landed as sketched. The second shipped as an equality test, and a review of the commit found that it guards every entry shape except the only one the table holds — the *Watch out* above is why, and it is where this item's own reasoning went wrong. It warned that a guard must not conflate "the parser said nothing" with "the override says nothing", which is true, and the comparison it implied does keep those apart. But `parse_object_schema` writes a type's key only `if fields:`, so no derived layout is ever empty, while every entry this table holds *is* an empty layout. Nothing about `[] == derived` can therefore ever be true: let the decomp give `RingCancel` a real CTOR and the cache be re-parsed, and `schema.get(109)` becomes a populated list, unequal to `[]`, so `schema[109] = []` would blank the fields the parser had just found with nothing raised. Standing in for that state confirms it: an `("AO", 84): []` entry leaves `game_setup("AO")` silent and `DoorFlame`'s three fields as `[]`. That stand-in is now `test_an_empty_override_cannot_blank_a_derived_layout`, which fails against the equality spelling and passes against what replaced it.

So the check is presence rather than equality: `tid in schema` means the parser derived something, and an entry whose whole charter is to supply what the CTOR expresses none of has nothing left to add. It subsumes the equality case instead of sitting beside it, and having no value comparison left it is indifferent to how a layout is spelled — the same duplicate written with tuples rather than lists slipped past the comparison, since the schema's rows come back from JSON as lists.

What presence gives up is that the table can only ever add a layout, never narrow one. Both entries it has ever held cost nothing by that rule: `RingCancel` has an `EMPTY_CTOR`, and ContinueZone's sole field computed below the payload base and was skipped, so the parser wrote no key for either — which is why ContinueZone showed as a `raw=` dump rather than a wrong layout ([30](item-030-well-base-fields.md)). A future need to correct a *partial* layout now fails loudly instead of applying silently, which is the right way round for a table meant to be temporary. AE has no layout overrides at all, so the guard is a no-op there.

**Where the sketch was wrong: reading `tlv_names` was not free.** `game_setup` resolved the schema on its *first* line, before the level cache it reads the AE names from — so at the moment the override was applied, the names the first check needs did not exist yet. The fix is an ordering one: `game_setup` now resolves the schema last, after the AO/AE branch that sets `tlv_names`, which nothing between them depended on. Nothing in that assignment says it has to come last, so the constraint is written beside it.

**The guard retired a test as well as gaining three.** `test_every_layout_override_targets_a_known_type` walked the shipped table asserting each tid was known — exactly the first check, and once the build itself raises, every test that calls `game_setup` covers it. What replaced it asserts the guard *fires*, on the pattern `_FIELD_TYPE_OVERRIDES` already had: an unknown type, a layout the parser derives, and the empty override over a derived layout that the equality spelling could not see. The two that need a donor read it from the committed cache rather than from `game_setup`, whose schema already carries the overrides — asking it for RingCancel's would hand back the override and prove nothing.
