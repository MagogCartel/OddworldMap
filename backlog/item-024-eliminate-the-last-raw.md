# 24. Eliminate the last `raw=`

**Status:** shipped 2026-07-23 · **Effort:** medium · **Where:** disc machine (builder plus a rebuild)

## What and why

The full-field extraction covered the gameplay set, but ~28 region types per game were still falling back to a `raw=` payload dump — the last places the map showed the reader bytes instead of fields.

## Decided

**Make the contract structural rather than a list.** `object_fields` returns a dict for any schema'd type — empty for the field-less ones — and `walk_obj_region` retires the raw fallback whenever `fields is not None`. So "no gameplay object shows `raw=`" holds by construction, and a new type cannot quietly reintroduce one. Pinned by a map-data invariant test.

**No array encoding.** The size cost came in small enough — gz +4.6% AO, +4.1% AE — that the repetitive-key encoding sketched as a contingency was never needed.

## Findings

**Two stragglers the allowlist alone could not reach**, both given `_SCHEMA_LAYOUT_OVERRIDES` entries:

- **ContinueZone**, whose `zone_number` is named `field_10` but sits at payload word 0 — `Path_TLV` is 0x18 wide, so the name's offset lands inside the rect. An explicit layout fixed it. This override was later retired by [30](item-030-well-base-fields.md), whose general below-base rule derives the identical layout.
- **The field-less AO RingCancel**, given an empty layout so it drops its padding dump. AE's `Null` decodes its own `padding` fields and needed no override.

Sidecars came out byte-unchanged, since every new field is an int and carries no game type.

## Shipped

The remaining gameplay-region types joined `GAMEPLAY_FIELD_TYPES` — scenery, AI bounds and stoppers, lifts and pulleys, sound/zone/load triggers, security devices, meat and bone sacks.

Surfaced the follow-up that became [30](item-030-well-base-fields.md): the AE wells' below-base fields, which were being dropped silently with no `raw=` to show for it.
