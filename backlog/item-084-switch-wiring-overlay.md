# 84. Switch wiring overlay

**Status:** open · **Effort:** large (viewer, product) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

Connection arrows ([1](item-001-connection-arrows.md)) show where you can *go*; nothing shows what a lever *does*. "What does this switch open?" is the single most common question anyone has staring at a screen of these games, the answer is fully present in the shipped field archive, and no wiki carries it — walkthroughs describe wiring in prose, one puzzle at a time. Drawing it would be the map's second circulation system: travel in one overlay, causation in the other.

## The data, measured (2026-08-07, from the shipped `map_data` files)

Producers — objects whose activation writes a switch id:

- AE: 807 (Lever 332, InvisibleSwitch 124, WorkWheel 114, FootSwitch 102, SlapLock 59 via `toggle_switch_id`, GlukkonSwitch 32 with separate `ok_switch_id` / `fail_switch_id`, one lone CrawlingSligButton, and the gates below).
- AO: 233 (Switch 101, InvisibleSwitch 84, BellSongStone 17, ChimeLock 13 with `password_switch_id` / `solve_switch_id`, IdSplitter 12 via `source_switch_id`, FootSwitch 4, BellHammer 2).
- The gates: AE's `WheelSyncer` (22) and `MultiSwitchController` (21) each carry `input_switch_id_1..6` → `output_switch_id` — literal logic gates, so real puzzle circuits (the wheel rooms, the multi-lever doors) are drawable, not just single wires.

Consumers — objects that answer to an id: Door (452 AE / 137 AO), SlamDoor (268), Drill (181), TrapDoor (150 + 29), ElectricWall (106 + 29), MovingBomb (`triggered_by_alarm`), BirdPortal (135, `create_portal_switch_id` / `delete_portal_switch_id`), Fleech (`wake_up_switch_id` / `can_wake_up_switch_id`), Mudokon (`angry_switch_id`), Slurg, StatusLight (319), and more.

Noise, also measured: `switch_id = 0` means unwired — AE holds 3,096 zeros against 2,528 live values — and some carriers are not consumers in any useful sense (LightEffect 811, Hoist 528+1109, ShadowZone). The overlay starts from a curated producer/consumer key table, not from every field whose name contains `switch_id`.

## Sketch

- `computeWiring(path)` in [js/model.js](../public/js/model.js), a sibling of `computeConnections`: edges from each producer's output id to every consumer field carrying that id within the path, reading the raw `fields` bucket (ints, snake_case — the archive, not `extra`). Skip id 0.
- Phase 1: 1:1 wires for the unambiguous pairs (levers/switches → doors, trapdoors, electric walls, slam doors, drills, portals' create/delete). Phase 2: the gates — `WheelSyncer` / `MultiSwitchController` render as fan-in nodes, `IdSplitter` and `GlukkonSwitch` as one-to-many with labelled outputs.
- Its own Display toggle beside Connection arrows, its own visual voice (the arrows own curves and solid strokes; wiring wants straight dotted runs or right-angle traces, so the two systems never read as one), hover spotlight exactly like `connFocus`.
- The tooltip gains the reverse reading for free: a consumer can name the producers pointing at it.

## Watch out

- **Id scope must come from the decomp before anything ships**: whether switch ids act path-wide or leak across paths of a level (the engine's switch-state array is global to the running level — verify what that means for cross-path wires the overlay would otherwise miss or invent).
- Same-key-different-meaning traps: a Slig's `slig_spawner_switch_id` binds it to its spawner's id space, not to a lever; `triggered_by` on FootSwitch is a filter, not an output. Every key entering the table needs its meaning checked against the decomp or the glossary, one by one — this is where the effort lives, and the curated table is also exactly the shape [17](item-017-field-glossary.md)'s definitions can annotate.
- Dense paths will draw a lot of wire: the spotlight-on-hover behaviour is the release valve, and a "wires only while hovering" mode may be the right default on phones.
