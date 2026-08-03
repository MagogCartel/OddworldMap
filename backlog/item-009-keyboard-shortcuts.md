# 9. Keyboard shortcuts

**Status:** shipped 2026-07-19 · **Effort:** small · **Where:** anywhere, viewer-only

## What and why

Panning and zooming had keys; everything else — stepping through a level's paths, flipping the display toggles — needed the mouse and the sidebar.

## Decided

**`[` / `]` are matched before the Alt guard.** On Option and AltGr layouts those characters arrive with a modifier set, so a guard that ran first would have silently swallowed them on exactly the keyboards that need them most.

**`?` opens the list on the shared dialog pattern** rather than a bespoke panel, so it inherits the focus trap and the close behaviour every other dialog has.

## Shipped

`[` / `]` cycle paths, `g` / `c` / `f` flip the grid, collision and foreground toggles, and `?` opens the shortcut overlay.
