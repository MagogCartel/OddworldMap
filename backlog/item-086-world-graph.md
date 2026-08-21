# 86. World graph

**Status:** open · **Effort:** large (viewer, product) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

Every cross-path and cross-level link is already computed and trusted ([40](item-040-validate-destinations.md)): the entry badges, the stub labels and the follows are all local glimpses of one graph nobody can see whole. A "how the game hangs together" view — every path a node, every door/well/portal/transition an edge — is the metro map of each game: navigation aid, completeness statement and the site's single most shareable artifact. It is derivable entirely from committed data; the work is presentation, not extraction.

## Sketch

- Aggregate: nodes are paths (AO 74; AE 92 with the 25 demo paths hidden per the setting — counted 2026-08-07 from the shipped data), edges are path→path with a count and the set of kinds (door / well / portal / transition), built from the same `destOf` + `destTrusted` walk `computeEntryPaths` does — one pass at boot per game, cached.
- Layout is the hard part and hand-tuning is legitimate: a column per level, in progression order where the transition graph can derive it, paths stacked within their column, edges bundled. [15](item-015-path-buttons-game-order.md) shipped a column whole: `levelOrder` in [js/pathorder.js](../public/js/pathorder.js) is the within-level walk in play order, and `levelEntry` says which path a column starts on. What it leaves is the order of the columns themselves, and a hub's spokes, which it lists by path id because nothing in the data ranks them. A force layout will produce spaghetti; don't start there.
- Surface: its own full-canvas mode (the map swaps out, the sidebar stays), not a dialog — the graph *is* a map. Click a node → `jumpToPlace`; hover an edge → the objects it aggregates. Colour edges by kind with the `CONN_COLORS` palette so the two views share a vocabulary.
- Phase 1 could be per-level: the current level's paths and their external stubs, opening from the level heading — smaller layout problem, immediate value, and it exercises the aggregation the full view needs.

## Watch out

- Demo paths sit outside the reachable graph; follow the setting and the entry-path rules rather than inventing reachability of its own.
- Ender levels make the AE graph honest but strange (the same geography appears twice under two ids); label sections the way the path buttons do rather than merging what the game keeps distinct.
- The graph must not contradict the pinned link counts in `tests/unit/map-data.test.js` — those tests are the aggregation's oracle, and a mismatch is a bug in the graph, not in the pins.
