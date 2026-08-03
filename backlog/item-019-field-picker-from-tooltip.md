# 19. Field picker from the tooltip

**Status:** shipped 2026-07-24 · **Effort:** tiny · **Where:** anywhere, viewer-only

## What and why

A follow-up nicety to [18](item-018-per-type-field-picker.md). With "Show more fields" on, configuring a Slig's fields meant leaving the Slig you were looking at and hunting for its row in the sidebar list. The affordance belongs where the object is.

## Sketch

Add a small "⚙ fields" control to an object's tooltip that expands that type's row in the Fields picker — scroll it into view, open its `<details>`. Pure viewer; the picker section and its per-type rows already exist.

## Findings

**The tooltip was the wrong host, and the screen list was the right one.** A floating hover tooltip cannot carry a control you have to travel to — the pointer leaves and it is gone — so the ⚙ went on the screen list's rows, which stay put and are also what touch has instead of a tooltip.

**Importing the picker would have closed a cycle.** The screen list reaching `fieldpanel.js` directly makes interaction → campanel → fieldpanel → interaction, so it dispatches a `reveal-field-type` window event instead and the picker listens.

## Shipped

With "Show more object fields" on, each object in a screen's list carries a ⚙ that opens the drawer, expands that type's row in the Fields panel and scrolls it into view.
