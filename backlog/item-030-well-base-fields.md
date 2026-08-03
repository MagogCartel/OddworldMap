# 30. AE well base fields, and the general below-base parser fix

**Status:** shipped 2026-07-29 · **Effort:** small (builder + rebuild) · **Where:** disc machine (AE rebuild)

## What and why

`parse_object_schema` took a field's payload word from the `field_XX` hex offset in its member name and skipped any name computing *below* the payload base, so those fields never reached the archive. ContinueZone was the one case that showed, as a `raw=` dump, and had been answered with an explicit layout override; the AE wells failed quietly, their four `Path_WellBase` members simply absent from all 266 of them.

## Findings

**The fix was a two-line deletion.** A base struct's members number from that struct's own start, which is the same lie the parser already handled the other way round when sequential members share one offset (Door's eight hub ids). Neither increases the offset, and `last` starts at `-1`, so the existing positional rule already answered both — the skip was the only thing in the way. One rule now handles a name that lies in either direction.

**ContinueZone's override retired with it**, and AO's `map_data` came out byte-identical, which is the proof the general rule reproduces exactly what the override hand-wrote. RingCancel's empty layout stays: a field-less type is not a below-base one.

**The de-dup is lossless, verified rather than assumed.** The new `switch_id` arrived under a name `tlv_extra_ae` had hand-decoded from the same payload word, and the display writes both buckets, so `extra` gave its copy up. Comparing every express well's old `extra.switch_id` against its new `fields.switch_id`: 185 of 185 match, and no `extra` key anywhere vanished without an archive copy taking it over. A test pins that no object names one key in both buckets.

**A correction to the original note on visibility.** It recorded "express wells' default view is identical", and that is not quite true. `fieldEntries` renders an `extra` value whenever it is neither null nor empty — a zero passes — while a `fields` value of zero is suppressed for `switch_id` by `HIDE_WHEN_ZERO`. So 46 of 81 local wells *gained* a switch id, and 74 of 185 express wells *stopped* printing `switch_id=0`. Both are improvements (a zero there means "no switch wired", which is what the suppression list exists for), and the net was judged below the changelog bar — but the default view did change, on more wells than the original count.

The "111 express wells would have printed it twice" figure is exactly right, for the same reason: only the non-zero ones would have rendered a duplicate.

## Shipped

All 266 AE wells gained `scale` / `switch_id` / `other_well_id` / `animation_id` at words 0–3, with nothing shifting.

**Left deliberately** → [41](item-041-inherited-field-types.md): the wells' `scale` arrives untyped, because `parse_member_types` reads a struct's own body and `Scale_short` is declared on `Path_WellBase`.
