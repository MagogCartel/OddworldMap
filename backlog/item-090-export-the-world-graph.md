# 90. Export the world graph as an image

**Status:** open · **Effort:** medium (viewer) · **Where:** anywhere · **Filed:** 2026-08-24, from [86](item-086-world-graph.md) shipping without it

## Why

[86](item-086-world-graph.md) calls the diagram the site's single most shareable artifact and then ships one way to share it: a link, which needs the site, a browser and a person willing to click. The two things anybody actually does with a diagram — paste it into a wiki page, drop it in a chat, print it — all want a file. The map has had both export buttons since [61](item-061-export-whole-path.md); the diagram, which is the one thing here small enough to be an image somebody keeps, has none.

Sizes are already the right shape for it: Oddysee's diagram is 3491 × 809 and Exoddus' 2799 × 896, both a fraction of the 4416 × 3360 the whole-path export already hands back.

## Why it is not the same job

The map exports because `paint` in [js/render.js](../public/js/render.js) draws into any canvas and [js/export.js](../public/js/export.js) hands it an offscreen one. None of that reaches the diagram: its nodes are DOM buttons and its edges an SVG layer, chosen in [86](item-086-world-graph.md) precisely so the keyboard, the ellipsis, the focus ring and `data-tip` came for free. So the export is a serialisation problem, not a second painter, and the shape of the answer is the decision this item exists to make.

## Sketch

Three routes, in the order they are worth trying:

- **Serialise to SVG and hand that over.** The truest to what is on screen and the only one that stays sharp at any size, which is what a poster wants. What has to be resolved on the way out: the page font (an SVG opened elsewhere has no `-apple-system`, so either embed the metrics-safe stack by name and accept substitution or convert the labels to paths), every `var()` colour (the tokens live in `:root`, so a copy needs them inlined), the node boxes (currently HTML, so they become `rect` + `text`, which is the bulk of the work), the arrow markers, and the counter-scaled level codes, which only mean anything at a scale the file does not have.
- **`foreignObject` around the existing DOM, then rasterise.** Cheapest to write and the least trustworthy: Safari's handling is poor and a font that fails to load renders blank rather than wrong, which is the failure [61](item-061-export-whole-path.md) already learned to probe for (`sizedCanvas` paints one pixel and reads it back because a blank canvas encodes to a perfectly good PNG).
- **Paint a canvas from the layout.** `graphLayout` already returns every route as a polyline and every node's box, so a painter reading it needs no DOM at all and would be maybe eighty lines. It costs a second renderer that has to be kept honest against the DOM one — the divergence [61](item-061-export-whole-path.md) avoided by having one painter and two canvases, and the reason to prefer SVG if SVG can be made to work.

Whichever wins, the button belongs beside the diagram's own `fit`, not in the sidebar's Display section: that section is hidden in graph mode because it acts on the map ([86](item-086-world-graph.md)).

## Watch out

- The diagram is not the map, so the export budget in [js/config.js](../public/js/config.js) (`EXPORT_MAX_PX`, `EXPORT_MAX_DIM`) is the map's own and reasoning from it needs care — but a raster export still has to answer what a browser will hand back, and the probe-before-paint lesson from [61](item-061-export-whole-path.md) applies whole.
- The demo-paths setting changes the diagram, so the file has to say which one it is or two exports of "Exoddus" differ by 25 nodes with nothing to tell them apart. The map's export names its place in the filename and can do the same here.
- What the hover produces has no business in a file, which is the rule `paint`'s `transients` flag already states for the map.
