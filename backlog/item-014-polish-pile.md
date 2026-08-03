# 14. Polish pile

**Status:** retired 2026-08-03 — three polish fixes shipped; the fourth was retired rather than built · **Effort:** tiny, batch when nearby · **Where:** anywhere, viewer-only

## What and why

Small viewer polish worth doing when a change was already in the neighbourhood: connection arrows on by default, `m` for the ruler, the off-screen tab stops, and connection-arrow stub labels colliding where several off-path objects share a cell.

## Retired

**The stub-label collision is real and unsized.** The sketch's answer was to spread or stagger the labels, and the only figure that ever sized the problem — 35 sub-60-unit stub clusters in AE — carries no date and nothing reproduces it. So the fix would be tuned against a measurement nobody has, which is why this is retired for the same reason [37](item-037-per-path-notes.md) was: an entry saying "improve this" with no threshold invites a forced change. A screen that visibly shows the collision is what would file it again, as its own item.

## Shipped

**Connection arrows on by default, 2026-07-24.** Flipped through the `tConn` HTML `checked` attribute, so a remembered display snapshot still overrides it. The trade-off was a richer first impression against a busier initial view for a new visitor; the toggle and the `a` shortcut still turn it off.

**`m` arms the ruler, 2026-07-24.** `r` was already the route planner, so the ruler took `m` for "measure" as a peer. It reuses the existing ruler toggle, so the route/ruler mutual exclusion holds without a second code path.

**Off-screen tab stops, 2026-07-27.** The collapsed drawer slid off-screen with roughly 50 controls still focusable, so Tab crossed all of them before reaching the map. `syncMenu` now sets `sidebar.inert` alongside the menu-button state, and moves focus to the menu button when the drawer closes underneath it — focus inside an inert subtree is otherwise lost to `body`. `/` had to start opening the drawer before focusing search, since focus cannot enter an inert subtree.
