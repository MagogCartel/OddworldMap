# 26. Value-rendering architecture

**Status:** shipped 2026-07-23 · **Effort:** medium · **Where:** builder re-parse plus viewer; no disc

## What and why

The base to lay *before* the big value-translation pass, so it would not force a rewrite afterwards. Two goals:

- **Every meaningful raw value renders readable.** Enum text for small sets (`start_direction` 0/1 → left/right), and a *conversion function* where the values follow a pattern rather than a fixed set (`shoot_on_sight_delay` takes 20+ distinct values from 0–240 across the shipped maps, so a static lookup is the wrong shape). A transform therefore has to be able to be either a map or a function.
- **Each mapping written once per shared meaning, with no collisions.** Slig, SligSpawner and SligGetPants share `start_state` and should share its enum; a Door's `start_state` is a lock state and must never borrow it.

The layer at filing was collision-safe but keyed semantic enums by `Type.field`, which forces listing every carrier — `SligSpawner.start_state` rendered raw because only `Slig.start_state` existed. That gap was the missing middle: no way to say "this enum belongs to the *group* of types sharing this field's type".

## Sketch

**Key value transforms by the field's game type — its C type in the decomp — not by object type.** One `TRANSFORM` table keyed by field type (`SligBrainState`, `DoorStates`, `Choice`, `Scale_short`), each entry a map or a function. Keying by type buys both goals at once: grouping, because one entry serves every object carrying a field of that type, and collision-safety, because unrelated fields have different C types. It also folds the old `VALUE_TRANSFORM` and `SEMANTIC_ENUM` into a single table, and `prettify` then needs no object type at all.

What it requires is that the field's type reach the viewer. `parse_object_schema` already sees the declared type in the relive_api blocks — capture it into the objects cache and ship a per-game field→type table. A re-parse, needing an `alive_reversing` checkout, but **not a disc rebuild**: `map_data` is unchanged, because the field type is pure metadata.

Sequenced one concern per commit: split the enum layer by axis; carry the type through the builder into a sidecar; re-key `prettify` and generalise resolution to map-or-function; then the content.

## Findings

**The content stopped being hand-written, which the sketch had not planned for.** Step 4 was going to be batches of hand-curated enum values. Instead the labels are *generated* straight from the decomp's enumerators into `enum_labels_{ao,ae}.json`, degrading to raw for unlisted values — so the content arrives with the source rather than being transcribed from it, and a relabelling upstream reaches the viewer through a regen.

## Shipped

Each field's game type reaches the viewer through a committed `field_types_{ao,ae}.json` sidecar (*Carry each field's game type into a viewer sidecar*, `949afeb`); `prettify` is re-keyed by that type into one map-or-function `TRANSFORM` table (*Key value transforms by the field's game type*, `1cd93a0`); and the enum content is generated from the decomp (*Generate enum value labels from the decomp*, `bdcc1a3`, plus refinements).

So a value's text is written once per game type and shared across every object that carries it, with unrelated same-named fields kept apart. The one branch left open is numeric units, which became [28](item-028-readable-units.md) — the untyped fields this architecture deliberately cannot reach.
