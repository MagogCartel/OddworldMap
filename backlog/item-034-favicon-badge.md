# 34. Favicon badge

**Status:** open — decided, needs rendering · **Effort:** tiny (asset) · **Where:** anywhere

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
