# 75. A schema layout override can go stale unnoticed

**Status:** open · **Effort:** small (builder) · **Where:** anywhere — the schema cache is committed, no disc · **Filed:** 2026-08-01 review, triaged 2026-08-02

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
