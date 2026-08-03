# 41. Type a field a struct inherits

**Status:** open — needs care · **Effort:** small (builder) · **Where:** builder-only, no disc — it changes `field_types_*` only

## What and why

`parse_member_types` reads a struct's *own* body, so a field declared on an intermediate base struct reaches the layout ([30](item-030-well-base-fields.md) saw to that) with no game type, and renders raw. The wells' `scale` is the live case: the decomp declares it `Scale_short field_0_scale` on `Path_WellBase`, and it shows `0`/`1` instead of `full`/`half`.

**Measured scope** (the only `Path_*` structs deriving from another are the two wells in both games, AE `Path_SlurgSpawner : Path_Slurg`, AO `Path_ScrabSpawner : Path_Scrab`): AE wells' `scale`, AE `ScrabSpawner`'s `scale` plus three `Choice_short` flags, AO wells' `scale`.

## Sketch

Changes `field_types_{ao,ae}.json` only; `map_data` is byte-identical either way, since types are metadata.

**Cheaper alternative if the labels are wanted sooner:** a targeted `_FIELD_TYPE_OVERRIDES` entry per field, the same mechanism SligSpawner uses — it corrects a type that exists, which is exactly this case. Overlaps [29](item-029-decomp-label-sweep.md)'s confirmed `scale` family: that item fixes bare-int declarations upstream; this one reads types the decomp already declares on a base struct.

## Findings

**The trap that makes it more than a one-liner:** AO's wells also inherit `field_24_off_level_or_dx`, whose type `OffLevelOrDx` is a **`union`**, not an enum. `parse_member_types`' sub-struct filter only recognizes names in `struct_names` (i.e. `Path_*`), so the union would pass into `field_types_ao.json` as a field type with no `enum_labels` entry — and `parse_enum_labels` scans `enum` definitions only, so it would never land in `bad` and `write_enum_labels`' loud failure would not catch it. Teach the filter about non-enum aggregates first.
