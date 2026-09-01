# 92. The member-type parser's remaining blind spots

**Status:** open · **Effort:** small to medium (builder), no disc · **Where:** anywhere with the checkout · **Filed:** 2026-09-01

## What it is

`parse_member_types` types a field by finding its declaration in a data struct's body. Three declaration shapes escape it, so eleven placed objects still render `scale` raw, and a few real enums ride with them:

- **A sub-struct arm.** Nine scales sit inside a `_data`/`_Data` struct whose owning member the `_data` filter drops while the CTOR reads one arm of it through a dot (`ADD("Scale", mTlv.mData.scale)` on the AO stones, `mTlv.field_10_data.field_1C_scale` on Teleporter): AO `BellSongStone`, `HandStone`, `MovieStone`; AE `Drill`, `FlyingSlig`, `FlyingSligSpawner`, `Slurg`, `SlurgSpawner`, `Teleporter`. `parse_object_schema` collapses the ADD's expression to its first segment, so the arm's own declared type is never consulted — for most of the nine it already sits in the member table (`Path_Teleporter_Data`, `Path_Drill_Data` and the stones' data structs are all swept), while Slurg's `Slurg_Path_Data` is not `Path_`-prefixed and needs the struct scan widened as well. Resolving the arm also types Slurg's `start_direction` (`XDirection_short`), Teleporter's `level` (`LevelIds`) and `cam_swap_effect` (`ScreenChangeEffects`), and retires the Drill `start_direction` override, whose "outside the Tlvs include graph" reason no longer holds — Drill.hpp is included and `Path_Drill_Data` sweeps fine. It is the same mechanism that would resolve the union arms [41](item-041-inherited-field-types.md) left unresolved: AO WellExpress's `off_level` is `LevelIds` behind the union's `.level` arm.
- **A `class`-declared data struct.** `Path_MovingBomb` is the one `class Path_*` in either game's swept headers, so its body is never read: its `Scale_short` scale and two `Choice_short` flags (`triggered_by_alarm`, `persist_offscreen`) ship bare, and MovingBomb is absent from `field_types_ao.json` entirely. The fix is one token — `\b(?:struct|class)\s+` — plus a cache regen; the access-specifier line carries no semicolon, so the member regex already skips it.
- **An uppercase member.** `SligGetPants` declares `Scale_short Scale;` and the member regex admits lowercase-initial names only. Widening it needs a sweep of what else an uppercase-initial match would admit before it ships.

## Why it matters

[29](item-029-decomp-label-sweep.md)'s missing-enum scan read the schema cache, which is blind to whatever this parser misses, and listed these as upstream misdeclarations — none is: every one declares its type somewhere the parser cannot see. Until the gaps close, eleven objects show `scale` as a bare 0/1 and the named enums render raw.
