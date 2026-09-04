# 93. SecurityClaw's archive labels sit one word to the left

**Status:** open · **Effort:** small (one corrections entry) plus the disc rebuild it waits for · **Where:** builder + rebuild, with a glossary touch-up when the keys move

**Filed:** found by [42](item-042-level-editor.md)'s relive schema sweep, whose struct-derived words disagreed with the ADD-order cache on exactly this type.

## What and why

AE's `Path_SecurityClaw` declares `Scale_int field_10_scale` — a 4-byte enum, which `ALIVE_ASSERT_SIZEOF(Path_SecurityClaw, 0x18)` confirms — so the member names after it lie about their offsets: `field_12_disabled_resources` really sits at 0x14 (payload word 2) and `field_14_unknown` at 0x16 (word 3). The schema parser trusts the names, so the shipped archive labels the scale's meaningless high word `disabled_resources` and the real disabled-resources word `unknown`, and the real `field_14_unknown` is never archived at all. The values are wrong under every placed SecurityClaw's tooltip today; nothing else reads them.

## Sketch

A `_SCHEMA_LAYOUT_CORRECTIONS` entry, the same mechanism MovieHandStone uses and the same high-word discipline (`Scale_int`'s upper half is dropped rather than kept as a phantom field):

- derived, as the parser yields today: `[[0, "scale", "Scale_int"], [1, "disabled_resources"], [2, "unknown"]]`
- corrected, the engine's own reading: `[[0, "scale", "Scale_int"], [2, "disabled_resources"], [3, "unknown"]]`

The names reach `map_data` at the next disc rebuild — batch it with the collision-link capture [42](item-042-level-editor.md) already owes that session — and the glossary keys move with them. The rebuild also spends [42](item-042-level-editor.md)'s `("AE", "SecurityClaw", "Unknown")` export fallback, whose word becomes archived.

The upstream path to retiring the entry is renaming the two members in `AliveLibAE/SecurityOrb.hpp` to their true offsets; the correction is keyed to today's derived layout, so that fix spends it loudly.
