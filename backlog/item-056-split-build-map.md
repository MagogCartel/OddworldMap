# 56. Split `build_map.py` into a package

**Status:** open · **Effort:** medium (builder refactor) · **Where:** anywhere for the split; verifying it needs a disc · **Filed:** 2026-07-24/25 review

## Symptom

[tools/build_map.py](../tools/build_map.py) is 1,536 lines (measured 2026-08-26) carrying seven unrelated concerns: ISO9660/LVL disc access, three separate C++-source parsers against the decomp, TLV payload decoding, the message-table extraction, MDEC/FG1 image assembly, PNG encoding, and the CLI. Navigating it means scrolling past four subsystems, and no concern can be taken on its own.

What is missing is addressability rather than importability. The module imports cleanly with no side effects, and [tools/tests/test_build_map.py](../tools/tests/test_build_map.py) already reaches its 79 top-level names that way. So a test of one parser loads the disc reader, the image codecs and the CLI along with it, and nothing can borrow a piece without taking all of it.

## Why now

[55](item-055-lint-and-test-tools.md) makes the pure functions testable; the split makes them *addressable*. Doing the split first without tests would be a leap; doing it after is mechanical.

## Sketch — target shape

```
tools/
  build_map.py          # thin CLI entry point: argparse, main(), the build loop
  oddmap/
    __init__.py
    paths.py            # HERE / ROOT / SITE / REPO / CAM2RGBA, derived once
    tables.py           # AO_LEVELS, AO_TLV_NAMES, AE_LEVEL_*, the static game data
    disc.py             # Disc, Lvl, parse_chunks
    decomp.py           # parse_pathdata_cpp_{ao,ae}, load_cache, int_rows, _match_brace, _strip_comments
    schema.py           # parse_member_types, parse_object_schema, parse_enum_labels, _derive_label,
                        #   load_object_schema, the override tables
    tlv.py              # tlv_extra_{ao,ae}, object_fields, walk_obj_region, GAMEPLAY_FIELD_TYPES
    messages.py         # string_table, extract_messages, message_json, write_messages
    image.py            # write_png, decompress_4or5, rgb555, decode_fg1, decode_cam, ensure_tools
    games.py            # the GAMES table and game_setup
    emit.py             # write_field_types, write_enum_labels, the sw.js stamp, print_build_summary
```

Keep `build_map.py` as the entry point so every existing invocation, the README, CLAUDE.md and muscle memory keep working.

**`emit.py` and `tables.py` are what keep the graph acyclic, and the obvious layout is what makes it not.** Two cycles hide in it. Filing `write_field_types` / `write_enum_labels` with the parsers they serve makes `schema` and `games` mutually dependent: both writers call `game_setup`, and `game_setup` calls `load_object_schema`. Filing the static game tables with `GAMES` does the same to `decomp` and `games`: `parse_pathdata_cpp_ae` reads `AE_LEVEL_DISPLAY` and `AE_LEVEL_ORDER`, while `game_setup` calls `load_cache`. Emitters are not parsers and data is not a profile, so each moves to the layer that only gets imported. What is left runs one way, and the CLI reaches everything.

## Watch out

**The module-level `OXIPNG` global** is set at import and `ensure_tools()` reassigns it via `global`. Moving `write_png` and `ensure_tools` to `image.py` while callers live elsewhere breaks that pattern quietly — the caller's module keeps its own stale binding if it does `from … import OXIPNG`. Convert it to a function-local lookup or a small module state object as part of the move, and make sure `ensure_tools()` is still called before the first `write_png`.

**`HERE` / `ROOT` / `REPO`** are derived from `__file__`. After the split, `HERE` computed from `oddmap/disc.py` points one directory too deep. Define them once in `paths.py` and import from there; do not recompute per module.

**CLAUDE.md's "Source vs generated" section is dense with function and constant names**, several with "correct it here, in the builder" instructions that must now point at a file. Updating that section is part of this commit, not a follow-up. Items here name the same symbols in prose, [42](item-042-level-editor.md) and [75](item-075-stale-schema-layout-override.md) among them, so the sweep covers `backlog/` too. Grep for each moved symbol.

**The caches must keep their paths.** `tools/data/{pathdata,objects}_{ao,ae}.json` are the delete-to-refresh contract described in CLAUDE.md. The split must not move them.

## Verify

The pipeline is byte-deterministic: build into a scratch dir with `--out` and `cmp` the data file against the committed one. Also run `--emit-field-data --out <tmp>` and `cmp` both sidecars for each game — that path needs no disc and can be verified anywhere. Both must be byte-identical; anything else means the refactor changed behaviour.

## Ships with

CLAUDE.md edits in the same commit. No changelog entry.
