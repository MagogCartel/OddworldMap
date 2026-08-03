# 35. Glossary tooltips on touch

**Status:** shipped 2026-07-30 — generalised the same day · **Effort:** small (viewer) · **Where:** anywhere — viewer-only

## What and why

The glossary reached the reader through a native `title`, which no phone shows, so the dotted underline promised an explanation touch could not collect — on the screen list, which is the surface touch has *instead* of a hover tooltip.

## Decided

**The tap coexists with what it activates rather than intercepting it.** Nothing calls `preventDefault`, so one tap both explains a field and ticks its checkbox in the picker, or jumps to its object in the screen list.

**Long-press stays rejected:** it fights the iOS selection callout, and it already means "copy this object's permalink" on the canvas. One gesture, one meaning.

**The seam is the attribute, not the class.** Delegating on `[data-tip]` rather than `.gloss` leaves the class holding only its dotted underline and cursor, so a second consumer writes an attribute and no JavaScript. Proved by hanging `data-tip` on a plain sidebar heading, which is not a `.gloss` and never will be.

**The line split stays in the module.** An attribute carries a string and nothing else, so the break is the only structure a consumer can express through this seam, and "first line summary, rest quieter" is a display convention rather than glossary knowledge. Moving it to the consumer would mean passing nodes, which means the registration API this deliberately does not have.

## Findings

**Two of the item's own guesses were wrong, and measuring corrected both.** It called an emulated `mouseover` a freebie: in fact a touch fires a real `pointerover` before its own tap and a `pointerout` after it, so an unfiltered pair shows the definition and hides it again inside one gesture. The `pointerType` filter is load-bearing, not defensive. And "position and clamp like `#tip`" does not survive contact — `#tip` is absolute inside `#main`, which clips inside `#sidebar` and `#camPanelBody`, both of which scroll. Same arithmetic, different containing block: a `<body>` child positioned against the viewport.

**Generalising forced one rule to change.** Leaving is asked of the anchor (`anchor.contains(relatedTarget)`) rather than re-resolved from the event target. For a span holding only text the two answers agree, which is why both shipped surfaces measure identically; for an anchor with element children the old rule hid the tooltip and showed it again each time the pointer crossed between them. Verified 2026-07-30 with a MutationObserver: zero hide events crossing between two child spans, and it still hides on leaving the anchor.

**Dropping `title` costs nothing that was ever announced.** Checked by putting a `title` back on a `.gloss` and reading the accessibility tree: Chrome's filtered tree does not expose it at all, and the enclosing row button's accessible name and description never carried it. It appears only in the unfiltered tree, as a `generic` node inside a button — somewhere no assistive technology navigating by interactive elements would land. Keyboard reach for these spans is still unsolved, exactly as it was under `title`.

**The `max-height` clip never bites.** The longest definition in the glossary renders 143px tall at 390px wide, so the `calc(100vh - 12px)` cap with `overflow: hidden` has room even in a 500px-tall window — which matters because `pointer-events: none` means a clipped tooltip could not be scrolled.

**One thing that works by accident rather than design:** nothing in the module observes its anchor being removed. Show a definition, then rebuild the screen list by changing path, and it hides — but only because Chrome fires `pointerout` on an element removed from under the cursor. On touch there is no such event; every touch route to a rebuild happens to pass through a `pointerdown` outside the anchor first, which dismisses it. No reachable stale case today; nothing states it either.

## Shipped

`js/anchortip.js` (born `glosstip.js`, renamed when it generalised), delegating on `[data-tip]` from the document. `#tip` deliberately untouched — the two write the same panel surface twice, and [21](item-021-css-design-inheritance.md) owned that fold.

**Recorded exclusion:** search result rows carry no glossary affordance on purpose. It is a scanning surface, `<mark>` highlights and dotted underlines would collide, and the definition is one jump away in context.
