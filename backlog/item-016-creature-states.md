# 16. Creature states

**Status:** shipped 2026-07-21 — then superseded in mechanism · **Effort:** small-medium · **Where:** disc machine (builder plus a rebuild)

## What and why

Mudokons, Sligs and Slogs showed raw payload words where the disc carries meaningful state. Verified against the decomp's `relive_api` structs (`Tlvs{AO,AE}.hpp`), all with named enums ready to copy:

- **AO Mudokon:** job (`Stand Scrub` / `Sit Scrub` / `Sit Chant`), direction, voice pitch, rescue switch id, deaf, persist. The confusable "praying" Mudokons in Monsaic are `Sit Chant`.
- **AE Mudokon:** state (`Chisle` / `Scrub` / `Angry Worker` / `Damage` / `Health Ring Giver`) **and** an emotion field with its own enum — the sad/angry/wired/sick states.
- **AO Slog:** asleep, wake/bark/chase anger, anger switch id. **Sligs:** `StartState` (sleeping/patrol).

## Sketch

Builder-side decode into named `extra` fields, following the `door#`/`well#` precedent, so the tooltip, camera panel and search (`job=sit chant`, `emotion=…`) all work with zero viewer changes.

## Ruled out

**Decoding `raw` viewer-side.** It would have shipped without a rebuild, but it creates a second decode layer contradicting the builder-owns-decoding pattern.

**A "rescuable" badge.** Sketched as viewer sugar and left unbuilt — the rescue switch id already answers the question in the tooltip.

## Findings

**The rescue-switch presence is the rescuable-set signal, and the sketch's confidence in it was too high.** The AO split is 11 sit-chant Monsaic scenery Mudokons against 12 that carry a switch — but that is a scripting hook rather than a rescuable flag, and it does not identify the 99. [71](item-071-mudokon-rescue-census.md) records the disproof in full; a future attempt starts from engine logic, not a data scan.

## Shipped

Two commits, one rebuild each, byte-verified against the discs on the disc machine. `rescue_switch_id` / `angry_switch_id` / `deaf` / `blind` are emitted only where the disc sets them; Slog `asleep` is emitted always, so a switchless awake Slog still decodes. Voice pitch, disabled resources, persist and the AI-tuning numbers were deliberately left out — they bloat hundreds of rows without describing the level. Schema tests pin both decodes and the no-raw invariant.

**Then the mechanism was superseded, and quickly.** The full object-field extraction moved job, state, emotion and start_state out of hand-written `extra` decodes and into the raw `fields` archive, prettified viewer-side — which is strictly better, since it means the disc is never needed again to surface or relabel one of these. What this item established survives: which fields are worth showing, and which were correctly left out.
