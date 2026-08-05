# 34. Favicon badge

**Status:** closed — built, tried in a real tab and declined; the icon stays as it is, recorded so it is not re-proposed · **Effort:** n/a · **Where:** n/a

## What and why

Give `favicon.svg` a solid **black circle** behind the Mudokon head, with the chin and hair poking slightly *outside* the circle.

## Decided

**Rendered and compared already, so the choice is made.** The circle *as* the badge — drop the rect, `<circle cx="32" cy="32" r="24">`. Head geometry spans x 12–54, y 10–58, so r24 puts the chin 2 units below the disc and the hair 4 above it, exactly the described silhouette, and it reads clearly at 16px. A tighter r22 lets the head's sides break the edge too, which turns the outline head-shaped rather than circular; r24 is the one.

## Sketch

- **The wrinkle it brings:** transparent corners are right for `favicon-96.png` (browsers composite on the tab bar) but wrong for `apple-touch-icon.png` — iOS flattens transparency to black and the black disc would vanish into it. That output needs its own opaque `#14161a` backdrop, so it stops being a straight rasterization of the SVG. Note it in [CLAUDE.md](../CLAUDE.md)'s static-files bullet when it lands. Also check `#sidebar h1 img`, which renders the same SVG at 24px against `--panel`.
- **Rasterizer:** `qlmanage -t -s 180 -o . favicon.svg` (then `-s 96`, then `oxipng -o 2 --strip safe`) reproduces the committed icons' look; checked against the committed `apple-touch-icon.png` (6727 bytes), near-identical output at 6266. CLAUDE.md's "a CoreGraphics Swift script was used" can't have parsed the SVG, so the two PNGs will shift slightly beyond the circle when re-rasterized with any tool — expected, not a regression. Worth replacing that hand-wave in CLAUDE.md with this recipe when it lands.

## Ruled out

- **The circle inside the existing rounded rect is a no-op.** `#000` against the rect's `#14161a` is not a contrast: at 96px you can just make out a disc, and at 16 and 24px — the sizes a favicon is ever seen at — it is indistinguishable from today's icon. Don't ship this and call it done.
- **`og-image.png` does not follow:** the card is text, a grid and marker boxes — it carries no Mudokon head at all, so there is nothing to restyle. Putting the icon on the card would be a separate idea.

## Findings

**The effect the whole idea rests on does not survive at favicon size** (measured 2026-08-05, by rasterizing the candidates to 32 device pixels and sampling the painted rows). The chin clears the disc by 2 of the icon's 64 units. A 16px favicon on a 2× display is 32 device pixels, so that is **1 pixel**. Of the two rows below the disc, the upper paints `rgb(79,94,75)` — dark enough to read as the disc's own antialiased edge — and the lower `rgb(160,200,149)`, only 161 units from light tab chrome. The single chin-coloured row therefore reads as antialiasing, and the disc's curve becomes the jawline: in a tab the head looks sliced flat across the bottom.

**The hair clears the disc by 4.63 units — 2.3 pixels, more than twice as far.** That asymmetry is the defect. The top tuft escapes and the bottom does not, so *Decided* above is wrong where it says the silhouette "reads clearly at 16px": that was checked for the disc, never for the protrusion the idea existed to produce. Nothing is clipped: the head's bounding box is x 11.7–52.3, y 10–58 inside a 64 viewBox, so the chin is drawn exactly as authored and *Decided*'s eyeballed x 12–54 was close enough not to matter. The sidebar masthead looked correct throughout, because it renders the same file far larger — which is why the fault stayed invisible until the icon was in a tab.

**The geometry was solvable, so this does not close as an obstacle.** Lifting the disc rather than shrinking it multiplies the chin while pushing the head's sides *further* inside the edge than the r24 original managed (`-2.54` units): `cy 30` gives 2 pixels of chin at `-3.06`, `cy 29 r23` gives 3 at `-2.42`, `cy 28 r22` gives 4 at `-1.58`. Shrinking at centre stays ruled out for the reason already recorded — at r22 the sides come within `0.54` units of the edge, which is what turned the outline head-shaped.

**A blood-red disc inside the kept squircle was the other candidate, and it answers the *Ruled out* note above:** red has a real contrast against `#14161a` where black had none, and keeping the squircle means no transparency, so `apple-touch-icon.png` rasterizes straight from the SVG and the wrinkle in *Sketch* is simply absent. Ten shades and radii were rendered. With the head at full size the red survives only as a rim, not a field, because the head is nearly as wide as the circle; scaling the head to `0.86` gives a genuine red field but abandons the chin-and-hair description altogether and shrinks the eyes, which are the whole recognition at 16px.

**Closed on taste, with both readings in front of the maintainer in a real browser tab.** The icon stays as it is. What is worth keeping from the attempt is the rasterizer recipe in *Sketch* and one gotcha for whoever does change the icon: `public/index.html` declares `favicon-96.png` alongside `favicon.svg`, so replacing the SVG alone leaves tabs disagreeing with each other until both PNGs are re-rendered. The two CLAUDE.md follow-ups the sketch asks for are moot, and CLAUDE.md was deliberately left untouched — the icon did not change, so its instructions are not wrong, only vaguer than this file.
