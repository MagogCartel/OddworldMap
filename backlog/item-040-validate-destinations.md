# 40. Validate a destination before trusting it

**Status:** shipped 2026-07-28 · **Effort:** small (viewer), in two commits · **Where:** anywhere — viewer-only, no rebuild

## What and why

A TLV whose destination *level* field was never set stores a 1, which reads as Necrum Mines, while its path and camera keep the values that were right for a link inside its own level. The triple looks plausible and the viewer believed it whole: the door at `SV P6 (825,600)` offered "click to follow to MI P6 C24" and, clicked, dropped you in the Mines. Sixty-one links in Exoddus named the Mines from another level and not one of them meant it.

## Sketch

`resolveTarget` already answered "is the object this link pairs with actually at that destination", and already returned null for every such case. Nobody asked it. Gate the follow, the tooltip's destination lines, the arrow stubs and `computeEntryPaths` on that answer wherever a link names a partner; a `PathTransition` names none and stays trusted as it is.

## Decided

**Cross-level only.** `resolveTarget` is camera-bounded with a path-wide fallback, so within a level an unresolved partner is that strictness rather than bad data — dozens of sound same-level follows turn on the distinction.

**`destOf` prefers the state that lands on another object** over the one that merely differs from the current path. An express well carries a destination per switch state, and a dead state is written two ways: naming the well's own id, or left at the address the fields were born with — level 1, path 1, camera 1, arrival well 0. That address is a real screen holding a placeholder well numbered 0, so the partner check waved 26 wells straight through a test that was working correctly.

**`targetAt` keys the unedited-address test on the level id, never on the pair number.** Monsaic Lines rides genuinely to `D1 P1 C1` and `F1 P1 C1` with an arrival well of 0; the narrower rule killed Paramonia, and the pinned entry sets caught it.

**Both sets are pinned whole**, not by count: entry slots (AO 17, AE 14) and cross-level follows (AO 17, AE 12, which is the games' level graph entire), so a regression names itself.

## Ruled out

**Reciprocity as the discriminator.** It looks like the obvious test for a live well state and it is wrong: `NE P5`'s two wells into the vaults have nothing pointing back and are genuine.

**Fixing it in the builder.** `tlv_extra` already withholds a non-travel BirdPortal's dead destination, which is the same defect treated at the source and more principled — but it costs a disc rebuild and cannot see other levels from inside one.

## Findings

Measured over the shipped data, 2026-07-28. Entry slots went AO 18 → 17 and AE 21 → 14. In Exoddus 61 objects outside the Mines named the Mines: 23 halves naming `MI P0`, 28 the opening screen. Only `WellExpress` objects changed destination — no door, teleporter, portal or transition moved, which matters because `destOf`'s new preference is general and could have disturbed them.

**The 79 launcher flips are a delta, not a population** (22 Oddysee + 57 Exoddus): objects whose `destOf` result went from carrying no target to carrying one, measured against the parent commit. A current-tree count of wells that resolve a partner gives 82 instead, which is why the figure looks unreproducible unless you know what it counts.

Those new pairings cannot be invented: a well target carries no `name`, so `resolveTarget` treats it as positional and skips the path-wide fallback, meaning every one of them is "a well with that id genuinely sits in the named camera" — the engine's own arrival rule.

**One genuine casualty, recorded rather than rescued.** `BR P10`'s `Door@500,860` names `MI P24`, and the same address read inside the Brewery lands exactly on `BR P24`'s `door# 10`, which points back at it: a real mutual pair whose level field alone was never set. Sweeping both games for that shape found exactly three silenced links that resolve inside their own level, and the other two (`SV P6`'s door, a `BR P23` well) resolve onto *themselves* — the path-wide fallback landing back on the source. Oddysee has none at all. So it is the only link in either game a local re-read would recover, and the partner pointing back is the discriminator that would make such a rescue safe. The limitation is in CLAUDE.md beside the rule that causes it.

## Shipped

Two commits, *Believe a cross-level destination only where its partner is* (`bae5155`) and *Take the well state that leads somewhere* (`4ef86b5`) — a follow-up rather than a fixup, because the mechanism differs: the first asks whether a destination is believable, the second asks which of an object's two destinations is live. Within the paths, 79 wells that read as pairing-less launchers now draw the pairing they name, so the Slig Barracks hub shows 6↔1, 5↔2, 8↔4, 7↔3 across its room instead of four stubs to the Mines.

Two paths it unblocked: [36](item-036-hide-demo-paths.md) inherited a clean entry set (two Mines demo paths had worn an entry badge on a dead link alone), and [15](item-015-path-buttons-game-order.md)'s "entry paths first" ordering is only as good as this set.
