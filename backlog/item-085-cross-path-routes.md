# 85. Cross-path route planner

**Status:** open · **Effort:** medium-large (viewer) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

Routes ([3](item-003-route-planner.md)) die at a path switch — deliberately, since a waypoint list in one path's draw space means nothing in another's. But the runs people actually plan cross doors: a speedrun segment is "through Zulag 2, take the well, finish in the hub", and today that is three separate routes and a sum done by hand. The route planner is the site's most speedrunner-shaped tool; this is its missing half.

## Sketch

- A route becomes a list of segments, `{lv, pa, pts}`. While the planner is armed, clicking a followable object closes the current segment at that object, follows it (the normal `navigateToDest`), and opens the next segment at the arrival partner — so the door itself is the seam, and the leg across it is a named transition rather than a drawn line.
- The bar totals per segment and overall; transitions list as "→ door to R1 P16" rows between segments. Undo pops a point, or a whole transition when it is last.
- Permalink: a `route2=` token carrying segments, alongside the existing grammar. `parseHash` ignores unknown segments by design, so old deployed viewers degrade to "no route" rather than to a broken one — the compatibility trap [3](item-003-route-planner.md) hit with its sketched `&route=` is the reason the token grows a version instead of mutating.
- The current clear-on-path-change listener inverts: a selection change *caused by the route's own follow* keeps the route; any other selection change still clears it.

## Watch out

- Distance semantics: legs are per-path world units (the games' unit sizes differ per game but not per path, so sums within one game stay honest); crossing games is out of scope and armed mode should refuse it.
- The hash is the state of record for routes; keep the segment encoding shortener-survivable the way `parseRoute`'s count-and-marker shape is.
- [86](item-086-world-graph.md) wants the same "which transition did you take" record; design the segment seam once, use it twice.
