# 85. Cross-path route planner

**Status:** shipped 2026-08-09 · **Effort:** medium-large (viewer) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

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

## Shipped

Largely as sketched — segments, the seam-on-follow, one marker grammar — with these departures and findings:

- The permalink shed the sketched `route2=` sidecar: no route link existed in the wild yet, so the marker grammar simply became `route=`, and a pathless pair-only body reads as no route. Every segment naming its path is what makes undo across a seam safe — it parks the route one path behind you, and a pathless token would have rebound its points to the wrong artwork.
- The bar stayed one line ("4 pts across 2 paths · …") rather than growing transition rows; the seams read off the map itself, where the polyline breaks. "Across N paths" counts distinct paths, because a same-path door pair seams two segments without leaving the path — same-path crossings fell out of the design for free and were kept, the break in the line being exactly what a door teleport is.
- The clear-on-path-change listener didn't need an inversion flag. One rule covers everything: the route lives while the selection stands on any of its segments' paths — so a shared link's recipient can walk the whole journey by button, door or the back button — and only a selection the route never visits clears it. Per-segment rendering is what makes the lenient rule safe: an aggressive clear exists to keep stale points off the wrong path's artwork, and a segment only ever draws on its own.
- The rule took `setLevel` to hold: `navigateToDest` reached a cross-level destination through `selectLevel`, whose default-path selection fires an intermediate `selection-changed` the rule rightly fails — and 17 of the games' 31 crossings land on a path that isn't its level's first. Targeted navigation now switches levels without electing a path, which also stopped search jumps double-firing.
- Undo takes an emptied segment's seam with it; hand stones and loopbacks stay plain waypoints (one shows a camera, the other travels nowhere); `routeArrive` anchors the far side on the resolved partner and quietly waits for a click when none resolves; `routeSeam` stops growing a full route, and the marker cap tolerates every state the writer can reach, so the token's writer and reader can never disagree.
- Two history bugs surfaced by watching the back button lose a follow, both fixed in `scheduleHash`: a pending push could be downgraded to a silent replace by the writes riding the follow's heels (push-ness is now sticky until the write fires), and the entry left behind held a stale route (the seam now `flushHash()`es first). Back retraces every crossing with the route as it stood.
- Cross-game seams cannot arise (no follow crosses games), so the distance sum never mixes unit scales.
