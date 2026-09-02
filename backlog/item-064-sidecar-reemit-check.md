# 64. CI check that the committed sidecars match a re-emit

**Status:** shipped 2026-09-02 · **Effort:** small (builder + CI) · **Where:** builder and CI, no disc · **Filed:** 2026-07-24/25 review

## What it is

`field_types_{ao,ae}.json` and `enum_labels_{ao,ae}.json` are generated and committed, and re-emitted on every normal build so they stay in sync. Nothing verifies that the *committed* files match what the *committed inputs* would produce. Edit `_FIELD_TYPE_OVERRIDES` or a `tools/data/objects_*.json` cache without re-emitting and the tree is quietly inconsistent until the next disc session.

## The blocker

Asymmetric reproducibility. `write_field_types` runs from the committed schema cache alone — no disc, no decomp — but `write_enum_labels` calls `parse_enum_labels`, which reads the `alive_reversing` checkout directly, so `--emit-field-data` as a whole cannot run in CI.

## Sketch if it goes ahead

Give the enum sweep the same cache discipline as `pathdata` and `objects`: a `tools/data/enum_defs_{ao,ae}.json` holding the parsed `(enums, bad)` result, regenerated only when deleted, requiring the checkout only then. Then `--emit-field-data` is fully reproducible from committed inputs, and CI becomes: emit into a temp dir, `cmp` all four files, fail on any difference.

## The decision to make

It adds two more committed cache files to a project that already carries four, in exchange for closing a drift window that has not actually bitten yet. The counter-argument is that it also makes the sidecars *verifiable by anyone without the decomp*, which is a real property for a public repo.

The region it touches is now `oddmap/schema.py`, which holds `parse_enum_labels`, and `oddmap/emit.py`, which writes both sidecars: the cache would sit beside the two the schema parsers already keep.

Note that [55](item-055-lint-and-test-tools.md) shipped a partial version of this: the field-types pair is re-emitted and byte-compared in CI already, and the enum-label pair skips without a checkout. So what remains is specifically closing the enum half.

## Shipped

The cache landed as the sketch proposed, with the discipline the other caches keep (re-parsed only when deleted), and the CI half turned out to already exist: the byte comparison was the `Sidecars` unittest all along, so "emit into a temp dir and `cmp`" reduced to deleting the two `@needs_decomp` decorators.

Where the sketch guessed wrong: the cache is `tools/data/enums_{ao,ae}.json` holding `{labels, bad}`, not `enum_defs_*` holding raw definitions — the raw defs never leave `parse_enum_labels`, and caching them would still need the checkout at emit time for the `AddEnum` curation. It caches every swept type (~260 per game) rather than the used subset, because pruning would make the cache a function of the schema cache and the override table, and an override edit would then need a checkout to re-emit — the exact drift window this item closes.

Two guards shipped alongside: a checkout-only freshness test pins the committed cache against a fresh sweep, so a stale cache after an upstream re-pin fails on any machine that has the checkout; and `_lib_headers` now refuses a missing tree instead of `rglob`ing it into a quietly thinner sweep — either game's cache reads both trees (the sibling fill-only fallback), so a partial checkout regenerating one was a real hazard.
