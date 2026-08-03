# 31. Settings overlay polish

**Status:** shipped 2026-07-29 · **Effort:** small (viewer), in two commits · **Where:** anywhere — viewer-only

## What and why

Eight settings in one flat column, each carrying a paragraph of description, had outgrown a single scan — and a reader could not tell a setting that ships off from one they switched off themselves.

## Decided

**Three sections** — *Saved on this device* / *Buttons and names* / *Objects and fields*, 3-2-3, with the cache toggle moved up beside the two other settings that keep something locally. Headed in the sidebar's own `h2` language so the dialog reads as part of the same system.

**`<section>` + `<h3>` over `<fieldset>`/`<legend>`:** every label is self-describing, so a group name is a scanning aid rather than disambiguation a screen reader needs repeated per control.

**Presence as the signal, not a hover tooltip.** A row whose value isn't its default carries `off by default` or `on by default` on its right edge; a row left alone carries nothing, so the right-hand column *is* the list of what you changed. A `title=` would have made the reader hover eight rows and compare for themselves, said nothing on touch where this dialog is thumb-driven, and added eight more of the affordance [35](item-035-glossary-tooltips-touch.md) was about to strip from `.gloss`.

**`bind()` drives the mark for the seven booleans**, so they are covered by construction; the show-more checkbox flips `fieldPrefs.mode` rather than a boolean and is the one wired by hand, which is the line a future setting could silently miss.

## Ruled out

A reset-all button. It would have to decide whether to discard the Fields picker's per-type picks, and eight checkboxes whose state you can now read need no bulk action.

## Findings

**The grouping judgement resolved on a measurement, not an estimate.** The scan cost was never the eight labels but the ~1,100 characters of description under them: with the headings in, the body measured 695px against a 667px box, so even a 1440×900 desktop was already scrolling. Widening the dialog to What's New's 460px bought back more than the three headings cost — 660px in 660px, no scroll on desktop. A 720px-tall laptop and a phone still scroll and cannot not: 660px of content will not fit in 80vh of a 720px window whatever the width.

The item's own worry about lopsided buckets came from a cut that included sidebar Display toggles (connection arrows, ruler, route) rather than settings, and left full-names and demo-paths unplaced. The real eight divide evenly, and [15](item-015-path-buttons-game-order.md)'s path-button order and [28](item-028-readable-units.md)'s units toggle each have an obvious home.

Verified 2026-07-29: the marks appear on exactly the changed rows and clear on flip-back; Tab reaches exactly the nine controls; at 390px no row wraps even with all eight marked, the tightest being "Remember display & object filters" beside "on by default". The dim text is 5.04:1 against the dialog, which clears AA for small text.

**One thing worth knowing rather than fixing:** because the mark sits inside the `<label>`, it joins the checkbox's accessible name — the tree reads `name: "Show demo paths off by default", checked: true`. That is accurate and better than hiding it from assistive tech, but the textbook shape is `aria-describedby`, which would announce it after the state and keep the name stable as the value flips.

## Shipped

Two commits, *Group the settings into three sections* (`2b5bcfe`) and *Say which settings differ from their default* (`3030a30`). A `settings.js` cleanup that was expected to fold in alongside — three copies of "write the settings object to storage" collapsing into the one helper — turned out to have shipped already, so nothing rode along.
