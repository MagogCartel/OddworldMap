# 7. AO menu level (S1)

**Status:** shipped 2026-08-07 · **Effort:** small-medium · **Where:** disc machine (builder plus a rebuild)

## What and why

The one completeness hole: `S1.LVL` exists on the AO disc with a `Path` chunk, but the decomp's path tables have null metadata for it, so the builder skips it (AE's `ST` menu renders fine, hence the asymmetry). The value is completeness only — it is a menu backdrop, not gameplay.

## Sketch

Self-discover the grid dimensions instead of reading the tables: infer `W`/`H` from the camera-name table length and the cam files present, and locate the object/collision regions by scanning. Keep it opt-in so a heuristic never touches the levels that have real tables.

## Shipped

`discover_path_meta` reads the grid off the path chunk: the camera-name table heads it at one 8-byte slot per cell, so the run of slots is the cell count, and the objects behind it choose among that count's factorisations, since every object has to land inside the grid. `S1` is 4x10, 18 cameras among 40 cells, 8 objects, no collision. The two transitions into it — `R1 P19` and `L1 P1`, the ones the attract-mode demos take — now follow, AO's entry slots go 17 to 18 and its cross-level follows 17 to 19, all re-pinned.

**Where the sketch was wrong, and what proved it.** It proposed inferring the grid from the name-table length *and the cam files present*; the cam files turn out to be unnecessary, because the objects alone leave exactly one factorisation standing. It also assumed the name table runs up to `obj_off`. Across the 190 paths that do have tables that is true of **four** — `AO C1 P1`, `AE ST P1`, `CR P1` and `CR P2` — and not by luck: they are exactly the paths carrying no collision, where `coll_off == obj_off` because there is nothing to sit between. Everywhere else the table ends at `coll_off` and 20-byte collision records fill the gap. Hunting that discrepancy is what produced the rule the code now uses, and both halves are checked against all 190: the slot run is each path's `coll_off` exactly, and the factorisation never contradicts a known grid. Guessing from one measured level would have shipped the wrong structural model.

**Why a collision-carrying path is refused** (measured 2026-08-07, both discs): starting the walk where the name table ends, all 186 paths that carry collision yield no origins at all — a collision record's first bytes land in the flags and length fields and fail the header test at once. With no origins to narrow it every factorisation stands, so the grid check raises. The four paths that *do* yield origins from that offset are the collision-free four above, reading their own genuine objects. A review round briefly recorded the opposite here — that collision bytes can parse as plausible objects, so the refusal came from the grid check rather than the walk — on those same four paths misread as evidence; the two figures are one set counted two ways.

Re-measured 2026-08-07 with `contiguous_objects`, which is what the code uses: the factorisation is unique for 57 AO paths and ambiguous-but-never-wrong for 16, and unique for 81 AE paths against 36. An earlier "58 and 15" here came from the resyncing walk instead, differing on `R1 P20` alone; the load-bearing half — never wrong — reproduces either way. Running `discover_path_meta` itself over all 190 tabulated paths raises on 189 and returns the right grid for the 1 it can read, so a path it cannot read is refused rather than mis-decoded.

**The two walks share their header test but not their reach.** Unifying that as well costs AO ten real objects across eight types — 182 lines of data — because the resyncing walk reads inside a region whose end it already knows and must accept a record overrunning an advisory end, while the strict walk is deciding that end and must not. The corroboration for the end it picks is the index table behind the objects, four bytes per cell: exact for `S1` at 524 + 40x4 = 684, true of every AE path and 61 of 73 AO ones. Slack on the rest is why a mismatch reports rather than raises.

**Opt-in became "only where a path has no table row"** rather than a flag. A flag would mean a plain `--game AO` no longer reproduces the committed data, and reproducing it is the property everything else here is verified against.

**What it retired.** No destination in either game now names a level the map does not render, so `annotations.json`'s `levels` section is empty in both and the tooltip's off-map-level branch is unreachable — [79](item-079-off-map-level-branch.md) holds that question. `S1`'s curated note moved from the level to `S1 P1`, since a level annotation exists to name a level the map never renders and this one is rendered; the test enforcing that is what caught it.
