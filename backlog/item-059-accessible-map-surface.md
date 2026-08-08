# 59. Give the map an accessible surface

**Status:** open · **Effort:** medium (accessibility) · **Where:** anywhere, viewer-only · **Filed:** 2026-07-24/25 review

## Symptom

Two related gaps.

*Assistive tech sees nothing.* `<canvas id="cv">` has no `role`, no accessible name, no `tabindex` and no text alternative. A screen-reader user gets an unlabelled graphic and no indication of what is on it or that anything changed.

*Keyboard users cannot inspect.* Arrow keys pan, `+`/`-` zoom, `[`/`]` cycle paths, and the display toggles have letter keys — but hovering, following a door, and opening the screen list are all pointer-only. Search is the sole keyboard route to an object, and it cannot answer "what is on this screen".

## Sketch, in two commits

*Commit 1 — announce state.* Add a visually-hidden live region and write to it on `selection-changed`:

```html
<div id="a11yStatus" class="sr-only" role="status" aria-live="polite"></div>
```

Content: game, level (full name), path, its curated or in-game name if any, and the object count — "Abe's Oddysee, Rupture Farms, path 15, Before Packaging, 283 objects". Everything needed is already computed for the sidebar. Also give the canvas `role="img"` and an `aria-label` carrying the same summary, so it is not an anonymous graphic when focus lands near it.

*Commit 2 — a keyboard route into a screen.* Bind a key (`l` for "list" is free; check against the existing map, since `g`, `c`, `f`, `a`, `r`, `m`, `i`, `/`, `?`, `[`, `]` are taken) that opens `openCamPanel` for the camera at the **view centre** rather than the pointer. `openCamPanel(x, y, focus)` already takes draw-space coordinates. The panel's rows are already `<button>`s, so once open it is fully navigable and each row jumps. Add the binding to the `?` overlay and the README controls list in the same commit.

## Watch out

**`.sr-only` does not exist in the stylesheet yet.** Add the standard clip-rect pattern rather than `display: none`, which removes it from the accessibility tree, or `visibility: hidden`.

**Do not make the canvas `tabindex="0"` without giving it something to do.** A focusable element that announces nothing on focus is worse than a labelled `role="img"`. If it becomes focusable later — for a roving-focus object cursor, which would be the real fix — that is separate, larger work.

**Announcement volume.** `selection-changed` re-fires for the same path on every pushed hash write. Announcing on every fire would make a screen reader chatter during ordinary browsing. Guard on an actual path change, the way `fieldpanel.js` and `campanel.js` already do.

**The place panel already announces this.** `#placePanel` ([js/place.js](../public/js/place.js)) is a live region carrying game, level, path and its name, so while it is open a global region would say the same thing twice. Make `#a11yStatus` the single announcer — drop the panel's `aria-live` when this lands — rather than gating one on the other. [39](item-039-where-am-i-surface.md) records the same obligation from its side.

## Related, already tracked

[14](item-014-polish-pile.md)'s off-screen tab stops were the third leg of this problem and have since shipped, so that part is done.

## Grown since filing

The By-the-numbers panel ([87](item-087-by-the-numbers.md)) brought two more: its count grid is styled spans carrying no table semantics for a screen reader, and `#numbersBtn` opens a panel without the `aria-expanded` / `aria-controls` pair `#placeBtn` models.

## Verify

VoiceOver on macOS or NVDA on Windows: load the page, tab to the map, switch paths, confirm the announcement fires once per real change and reads sensibly. Then unplug the mouse and try to answer "what is on screen R1 P15 C04" using only the keyboard.

## Ships with

A README controls-list update and a `changelog.json` entry, tag `improved`, for the keyboard binding. The live region alone is arguably invisible to most, but it is still a user-facing capability — an entry is justified.
