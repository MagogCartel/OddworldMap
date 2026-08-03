# 32. Dynamic-update listener sweep

**Status:** shipped 2026-07-24 · **Effort:** small · **Where:** anywhere, viewer-only

## What and why

Some surfaces did not refresh when a related control changed, so they needed a manual reopen. The known instance: with "Show more object fields" on, search for an object, then tick a new field for that type in the Fields picker — the open search rows did not pick the field up.

Distinct from [27](item-027-search-in-user-representation.md), which is about *which representation* search matches in. This is about *when* a dependent view re-renders at all.

## Sketch

Sweep for places where a `settings-changed`, field-prefs or selection change should trigger a re-render and does not, and wire the missing listeners.

## Findings

**The picker's silence was deliberate and had to stay**, which is what made this more than adding an event. The picker keeps its own edits local so an open row does not collapse under its own edit — so the fix is an event the picker emits and *its own listener ignores*, rather than a general re-render.

## Shipped

The picker emits `settings-changed {key:"fieldPicks"}`, a key its own listener ignores, so the open row survives. Search re-runs on the show-more mode toggle and on picks, not just on raw-values; the screen list rebuilds on picks too.

## Ruled out

**The hover tooltip.** It is transient, and reaching the picker hides it — there is nothing there to keep up to date.

**Search grouping going stale on path navigation.** That is a selection axis, not a field-prefs one, so it belongs to a different question than this sweep.
