# 64. CI check that the committed sidecars match a re-emit

**Status:** undecided — needs a decision before anyone builds it · **Effort:** small (builder + CI) · **Where:** builder and CI, no disc · **Filed:** 2026-07-24/25 review

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
