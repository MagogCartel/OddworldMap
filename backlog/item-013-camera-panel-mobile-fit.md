# 13. Camera panel mobile-fit and row highlight

**Status:** shipped 2026-07-19 · **Effort:** small-medium · **Where:** anywhere, viewer-only

## What and why

The screen list ([4](item-004-per-camera-object-list.md)) covered a phone screen entirely, which is the worst possible shape for a panel whose whole job is to describe what you are looking at. And on touch there is no hover, so tapping an object had to do what a tooltip does with a mouse.

## Decided

**A bottom sheet capped at 40% height on narrow screens**, with the map staying visible above it. Jump destinations land above the sheet, since the canvas centre sits at 50%.

**Tapping an object opens the list scrolled to that object's highlighted row.** That makes the panel the touch equivalent of the tooltip rather than a second, separate affordance.

**The panel stays open on row jumps at every screen size**, so working through a screen's objects one at a time does not mean reopening it each time.

**On by default** (`screenList: true`), with a Settings switch to turn it off — the one panel that earned the default-on spot, because a tap that does nothing reads as a broken map.
