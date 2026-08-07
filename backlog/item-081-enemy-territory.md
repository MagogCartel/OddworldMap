# 81. Enemy territory rendering

**Status:** open · **Effort:** small-medium (viewer) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

The invisible walls that pen enemies in are in the data and on the map, but unreadable: `SligBoundLeft` / `SligBoundRight` (186 + 175 in AO), `EnemyStopper` (156 AO, 150 AE) and `ScrabNoFall` all land in the Meta bucket, off by default, and when switched on they render as anonymous grey boxes indistinguishable from `ShadowZone`s. "How far can that Slig chase me?" is exactly the question a route reader is asking, and the answer is sitting in the default-off pile wearing a disguise.

## Sketch

- Phase 1 is a *reading*, not new data: draw the bound types as what they are — a vertical barrier line spanning the marker's height (or the camera's, where the marker is a sliver), dashed, in the enemy category's colour, with a small left/right tick for the side it blocks. Visibility rides the Enemies category toggle rather than adding a new one: the barriers are enemy semantics.
- The types stay in their current category buckets for filtering and search; only their rendering specializes. The tooltip already names them.
- Phase 2, only if wanted: infer a patrol band per Slig — the span between the nearest facing bound pair in its camera row — and shade it faintly on hover. That is an engine-behaviour claim, not a data dump.

## Watch out

- Phase 2's pairing rule must come from the decomp, not from eyeballing: which bound stops which enemy kind (`EnemyStopper` carries fields; `SligPersist` is a different concern entirely), and whether bounds act path-wide or per camera. Do not ship a shaded band on a guess — a wrong band is worse than no band, and [71](item-071-mudokon-rescue-census.md) is the standing example of a field that did not mean what it looked like.
- AO and AE name and split these types differently; match by name per game and keep the drawing rule shared.
