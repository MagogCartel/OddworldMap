# 71. Mudokon rescue census

**Status:** closed — premise disproved, recorded so it is not re-proposed · **Effort:** n/a · **Where:** n/a · **Filed:** 2026-07-24/25 review

## What was proposed

A rescue checklist keyed on `rescue_switch_id`, distinguishing rescuable Mudokons from scenery.

## Premise disproved

The maintainer had already tried this and reported that the field is not a rescuable marker. A scan of the shipped data confirms it decisively:

| game | Mudokons | with non-zero `rescue_switch_id` | without |
| --- | --- | --- | --- |
| AO | 110 | 12 | 98 |
| AE | 379 | 73 | 306 |

AO's good ending requires 99 rescues and only 12 Mudokons carry the field, so it cannot be the signal. The maintainer's reading — that it identifies Mudokons whose rescue toggles a specific switch, a scripting hook rather than a rescuable flag — fits the distribution.

## Where a future attempt would have to start

The rescuable set is presumably determined by engine logic — which Mudokon types count, which paths are scored, whether the object is in a rescuable state — rather than by a single TLV field. So it is a decomp research question, not a data-scan question.

Fields actually present on Mudokons, for whoever looks. AO: `deaf`, `disabled_resources`, `job`, `persist_offscreen`, `rescue_switch_id`, `scale`, `start_direction`, `voice_pitch`. AE: those plus `angry_switch_id`, `blind`, `emotion`, `gets_depressed`, `give_ring_without_password`, `persist_reset_offscreen`, `ring_pulse_interval`, `state`, `work_after_turning_wheel`.

Related: [16](item-016-creature-states.md) parked a "rescuable badge" for the same reason, and [17](item-017-field-glossary.md) assumes the "not one of the rescuable 99" distinction is knowable — it currently is not.
