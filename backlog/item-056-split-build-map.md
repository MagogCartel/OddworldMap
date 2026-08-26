# 56. Split `build_map.py` into a package

**Status:** open · **Effort:** medium (builder refactor) · **Where:** anywhere for the split; verifying it needs a disc · **Filed:** 2026-07-24/25 review

## Symptom

[tools/build_map.py](../tools/build_map.py) is 1,536 lines (measured 2026-08-26) carrying seven unrelated concerns: ISO9660/LVL disc access, three separate C++-source parsers against the decomp, TLV payload decoding, the message-table extraction, MDEC/FG1 image assembly, PNG encoding, and the CLI. Navigating it means scrolling past four subsystems, and nothing can be imported in isolation.

## Why now

[55](item-055-lint-and-test-tools.md) makes the pure functions testable; the split makes them *addressable*. Doing the split first without tests would be a leap; doing it after is mechanical.

## Sketch — target shape

```
tools/
  build_map.py          # thin CLI entry point: argparse, main(), the build loop, print_build_summary
  oddmap/
    __init__.py
    disc.py             # Disc, Lvl, parse_chunks
    decomp.py           # parse_pathdata_cpp_{ao,ae}, load_cache, int_rows, _match_brace, _strip_comments
    schema.py           # parse_member_types, parse_object_schema, parse_enum_labels, _derive_label,
                        #   load_object_schema, write_field_types, write_enum_labels, the override tables
    tlv.py              # tlv_extra_{ao,ae}, object_fields, walk_obj_region, GAMEPLAY_FIELD_TYPES
    messages.py         # string_table, message_json, write_messages
    image.py            # write_png, decompress_4or5, rgb555, decode_fg1, decode_cam, ensure_tools
    games.py            # the GAMES table, AO_LEVELS, AO_TLV_NAMES, AE_LEVEL_*, game_setup
```

Keep `build_map.py` as the entry point so every existing invocation, the README, CLAUDE.md and muscle memory keep working.

## Watch out

**The module-level `OXIPNG` global** is set at import and `ensure_tools()` reassigns it via `global`. Moving `write_png` and `ensure_tools` to `image.py` while callers live elsewhere breaks that pattern quietly — the caller's module keeps its own stale binding if it does `from … import OXIPNG`. Convert it to a function-local lookup or a small module state object as part of the move, and make sure `ensure_tools()` is still called before the first `write_png`.

**`HERE` / `ROOT` / `REPO`** are derived from `__file__`. After the split, `HERE` computed from `oddmap/disc.py` points one directory too deep. Define them once in the package and import from there — do not recompute per module.

**CLAUDE.md's "Source vs generated" section is dense with function and constant names** — `parse_enum_labels`, `parse_member_types`, `parse_object_schema`, `object_fields`, `write_field_types`, `_FIELD_TYPE_OVERRIDES`, `_SCHEMA_LAYOUT_OVERRIDES`, `GAMEPLAY_FIELD_TYPES` — several with "correct it here, in the builder" instructions that must now point at a file. Updating that section is part of this commit, not a follow-up. Items here name the same functions in prose — [42](item-042-level-editor.md) leans on `parse_object_schema`, `parse_pathdata_cpp_{ao,ae}`, `positional_rows`, `decode_cam` and `Disc.sector`, and [75](item-075-stale-schema-layout-override.md) on both override tables — so the sweep covers `backlog/` too.

**The caches must keep their paths.** `tools/data/{pathdata,objects}_{ao,ae}.json` are the delete-to-refresh contract described in CLAUDE.md. The split must not move them.

## Verify

The pipeline is byte-deterministic: build into a scratch dir with `--out` and `cmp` the data file against the committed one. Also run `--emit-field-data --out <tmp>` and `cmp` both sidecars for each game — that path needs no disc and can be verified anywhere. Both must be byte-identical; anything else means the refactor changed behaviour.

## Ships with

CLAUDE.md edits in the same commit. No changelog entry.
