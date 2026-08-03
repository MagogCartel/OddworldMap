# 28. Readable units for raw numeric fields

**Status:** open · **Effort:** medium (curation plus a disc-machine spike) · **Where:** the safe and middle tiers anywhere; the seconds tier needs an emulator session

## What and why

Most enum fields now render as words, but bare-int numeric fields still show raw: ~40–60 timer/delay fields per game as of 2026-07 (`shoot_on_sight_delay`, `pause_time`, `panic_timeout`, `chase_delay`, …), a few percentages (`percent_say_what`, `percent_beat_mudokon`), a few distances (`noise_wake_up_distance`, `grid_spacing`). They carry **no game type**, so the type-keyed transform layer (`TRANSFORM` / `enum_labels`) can't reach them.

## Findings

**What the decomp gives (checked 2026-07):** units are *not* systematically annotated — only a handful of ADD display names carry one (`(Grids)` on `noise_wake_up_distance` and `patrol_range`, `(Seconds)` on exactly one field, `mines_alarm_countdown`); the rest are unlabelled. And there is **no fixed logic frame rate** — `Calculate_FPS_495250` *measures* elapsed time (a debug counter), not a constant. The timers are frame counts, decremented per game loop (15/30/60/90 patterns), but "how many equal one second" is not in the source.

## Sketch

**Tiers, cleanest first:**

- **Safe now:** `percent → "%"` (raw is already 0–100) and pass-through of the two decomp-annotated units. Small — may not justify a units layer on its own.
- **Middle — "N frames":** label timer/delay fields `N frames`. Accurate (they *are* frame counts), no FPS needed; costs a *reviewed* list of which untyped fields are frame-timers (name heuristics `*_delay`/`*_time`/`*_timeout` get most, but a blanket rule mislabels the `*_time` fields that are counts).
- **Full — timers → seconds:** the marquee, blocked on the real logic rate. **Disc-machine spike:** in DuckStation, watch a timer that is *also* labelled `(Seconds)` (the mine countdown) decrement and derive frames-per-second from it, then convert. A guessed factor would ship "silently wrong" seconds — the thing the exporter now fails loudly to prevent.

**Plumbing (reuses the architecture):** untyped fields get a synthetic unit type via an override table `(game, object, field) → "Frames"/"Percent"/"Grid"`, mirroring `_FIELD_TYPE_OVERRIDES` in `build_map.py`; add a `TRANSFORM` *function* per unit in [js/fields.js](../public/js/fields.js) (`Percent: n => `${n}%``). The `resolve` map-or-function path already supports functions (unit-tested), so the code is small — the work is the curated field→unit table and, for seconds, the measured FPS.

## Ruled out

**In-page FPS switcher (30/60/custom):** wrong for a reference map — it offers a choice around a value that has one true answer nobody has measured yet, and a reference should state the fact rather than ask the reader to pick. Recorded so it isn't re-proposed; measure the real rate once instead.
