# 39. A surface for "where am I"

**Status:** shipped 2026-07-28 · **Effort:** small (viewer) · **Where:** anywhere — viewer-only

## What and why

Thirteen paths carried a curated note and nothing showed it, and on a phone the closed drawer left nothing on screen saying where you were at all. Three surfaces had already been built and taken back out: the path button's `title` (invisible on touch), a line under the path row (a phone closes the drawer on the pick, and on desktop it read as an unattributed sentence), and a toast (transient, and silent on a permalink arrival).

## Decided

**A chip, not a bare `ℹ` button.** A generic glyph means nothing until it is clicked; a chip answers half the question by existing, which counts most on a phone.

**Nothing opens by itself**, permalink arrivals included — the dot on the chip is the invitation. That is also how the marker question landed on reconsideration: on the chip a marker is the only thing saying there is something to open, so it informs, while on a path button it would point at a disclosure living somewhere else, so it stays declined.

**The panel stays open across a selection change and re-renders**, diverging from the screen list, whose content is one coordinate's inventory rather than the selection itself. Following a door or cycling with `[`/`]` keeps it answering.

**Deliberately not `.chrome`.** An embed, sidebar closed inside someone else's page, is where "which level and path is this" is hardest to answer otherwise.

## Findings

**The chip's width is arithmetic, not taste.** `max-width: min(340px, calc(100% - 152px))`, where 152 is 54px of left offset plus two 34px corner buttons and two 10px gaps. The first attempt used `calc(100% - 64px)` and overlapped the copy-link and What's New buttons below about 460px — and because the chip paints above them, an overlap makes them unclickable rather than merely untidy. Check the geometry on the longest label either game has, at 390px and narrower; a representative path is short enough to hide a width regression.

**A live region announces only what is written into it while it is visible**, and that bit twice. `place.js` is imported *by* `interaction.js`, so its `selection-changed` listener runs first: on a narrow layout it filled the panel while the open drawer still had it at `display: none`, and only then did the drawer close. Picking a path from that drawer is the one way you pick a path on a phone, so the announcement was lost on the most common route. Pressing `i` under the open drawer had the same shape from the other direction.

The obvious cheap fix does not work: `visibility: hidden` removes an element from the accessibility tree exactly as `display: none` does, so the mutation still goes unannounced. What does work is deferring — `syncPlace` fills only when the panel is both open and actually rendered (`panel.offsetParent`), and `toggleMenu` calls it when the drawer lifts. Routing `setOpen`'s fill through the same guard covers the `i` case too, which leaves `fill` with exactly one caller and the invariant enforced in one place. Verified 2026-07-30 with a MutationObserver at 390×844: picking a path from the drawer produces one write, with the panel on screen.

**`#routeBar` is wider than the middle of a phone screen**, so capping the chip's width cannot clear it; the chip steps down a row while a route is armed instead.

## Shipped

`js/place.js`, `#placeBtn` + `#placePanel`: the chip names the current level and path, wears an accent dot where the path carries a note, and click, tap or `i` discloses the game, the level's full name, the entry-point flag and the note as prose. The route-bar step-down is recorded in CLAUDE.md; the live-region fill order was retired with the panel's `aria-live`.

[59](item-059-accessible-map-surface.md)'s global `#a11yStatus` took the announcing over on 2026-08-22, and the panel gave up its `aria-live` along with the deferral built for it — a panel nobody is listening to can be filled under cover, so `syncPlace` needs neither `panel.offsetParent` nor the call from `toggleMenu`. What the dot says now reaches a screen reader with the rest of the place, and `i` puts the keyboard in the panel, since a disclosure nothing announces has to be somewhere focus can land.
