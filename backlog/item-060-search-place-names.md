# 60. Search should know place names

**Status:** open · **Effort:** small (viewer, product) · **Where:** anywhere, viewer-only · **Filed:** 2026-07-24/25 review

## Symptom

Searching `monsaic`, `paramonia`, `zulag 2`, `feeco` or `necrum` returns **zero hits**. `tlvSearchText` in [js/search.js](../public/js/search.js) indexes object name plus decoded fields only — level and path names are not in the index at all. Those are the words a player reaches for first, and the sidebar's level and path buttons are the only way to use them.

## Sketch

Add a "Places" group rendered *above* the object groups in `runSearch`:

1. Build the candidate list from `state.games` → levels → paths: for each level, `L.short` and `L.name`; for each path, `pathDisplayName(G.id, L.short, P)` plus the `LV Pn` code form.
2. Match with the existing `matchesQuery` against a lowercased `"<short> <name> <path label>"` blob, and rank with `rankFor`.
3. A hit renders as `AO · L1 P3 — The Chant Gate` and on click selects that path — reuse `selectPath` through a small exported helper rather than duplicating the selection logic.
4. Respect the scope bar: "Places" is meaningless under `path` scope, so hide the group there, or under `level` scope show only that level's paths.

## This gets better for free as annotations land

Reading through `pathDisplayName` ([js/annotations.js](../public/js/annotations.js)) means the curated-name-overrides-in-game-name precedence is already handled, and every path name added under [12](item-012-curated-path-names.md) becomes searchable with no further code change. That is the reason to route through `pathDisplayName` rather than reading `P.name` directly.

Whatever [77](item-077-what-a-place-is-known-for.md) settles on belongs in the same blob, and is the half of this that reaches a player who knows what a place is like but not what it is called. Measured 2026-08-04: `tear`, `x-tractor` and `high security` return nothing today, while `slig` alone returns 819 object hits — which is why the Places group has to be counted and capped apart from the objects rather than merged with them.

## Coverage — read the data, not the number below

At the review this recorded AO at 41 of 73 curated and AE at **0 curated, 104 unnamed**, and concluded the feature would be "mostly a level-name search" on Exoddus. **That is no longer true and was the review's most stale figure.** Measured 2026-07-31, AE is at 114 of 117 paths curated, and no AE path carries a disc `name` at all, because [38](item-038-path-section-tag.md) moved the thirteen ender labels into `section`. Recompute from the shipped data before sizing this; [12](item-012-curated-path-names.md) holds the current counts.

## Watch out

**Group ordering and the hit cap.** Places must not consume the `HIT_CAP` budget or the per-group `GROUP_MAX` slots meant for objects; count and cap it separately. There are only ~200 places, so no cap is really needed.

**The summary line** prints a per-game object hit count. Decide whether places count toward "N hits" — the recommendation is no: keep the summary about objects and let the Places group carry its own count in its header, the way the other group headers already do.

**The empty query path.** `runSearch` bails under 2 characters; keep that.

## Verify

`monsaic` → the L1 level and its paths. `zulag 2` → AO R2's four Zulag 2 paths. `slig` → unchanged object behaviour, no Places group. `P3` → sensible, not noise.

## Ships with

A README search bullet update and a `changelog.json` entry, tag `new`.
