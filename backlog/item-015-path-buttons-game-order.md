# 15. Path buttons in game order

**Status:** open · **Effort:** small (a setting) · **Where:** anywhere, viewer-only

## What and why

Path buttons sort by id, which interleaves areas (R2 shows Zulag 2/4/3/3/4/3… before Zulag 1).

## Sketch

A setting to sort them by in-game progression where derivable: entry paths first, then a walk of the transition graph (`computeConnections`/`computeEntryPaths` already know the edges); fall back to id order for paths the graph can't order.

Both preconditions this needed have cleared: [40](item-040-validate-destinations.md) made the entry sets sound to sort by, and the Exoddus names are in. Curated names grouping identically (all "Zulag 3 — …" adjacent) may still get most of the value cheaper — but [38](item-038-path-section-tag.md) moved the ender tag out of the name into `section`, so for those thirteen the grouping key is the section, not a prefix on the name.
