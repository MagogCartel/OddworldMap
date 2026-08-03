# 7. AO menu level (S1)

**Status:** open · **Effort:** small-medium · **Where:** disc machine (builder plus a rebuild)

## What and why

The one completeness hole: `S1.LVL` exists on the AO disc with a `Path` chunk, but the decomp's path tables have null metadata for it, so the builder skips it (AE's `ST` menu renders fine, hence the asymmetry). The value is completeness only — it is a menu backdrop, not gameplay.

## Sketch

Self-discover the grid dimensions instead of reading the tables: infer `W`/`H` from the camera-name table length and the cam files present, and locate the object/collision regions by scanning. Keep it opt-in so a heuristic never touches the levels that have real tables.
