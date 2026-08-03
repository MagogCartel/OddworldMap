# 61. Export the whole path, not the viewport

**Status:** open · **Effort:** medium (viewer, product) · **Where:** anywhere, but test the size limits on a real iPhone · **Filed:** 2026-07-24/25 review

## What the current button actually does

`cv.toBlob` in [js/sidebar.js](../public/js/sidebar.js) copies **the pixels currently on screen**. So "Export view as PNG" is a screenshot: cropped to the window, at whatever zoom happens to be set, at `devicePixelRatio` scaling, including whatever slivers of neighbouring screens are visible and excluding everything scrolled out of frame. To get a whole level today you must zoom out until it fits — which downsamples 368×240 artwork until the objects are unreadable — and you still get window letterboxing around it.

## What is proposed instead

A second export that renders the **entire current path** into an offscreen canvas at 1:1 and downloads that: `path.w * CELL_W` × `path.h * CELL_H` pixels, every camera laid edge to edge at native artwork resolution, with the overlays the user currently has enabled drawn on top. No window, no crop, no zoom loss. For AO R1 P15, 12×3 cells, that is a 4416×720 PNG containing all 20 screens.

## Why it is worth building

This is the artifact people actually want from a map site — the thing that gets posted to a wiki, a forum thread or a speedrun guide, printed, or annotated in an image editor, with the site's URL implicitly attached to it. The viewport screenshot is a debugging aid by comparison. It also composes with everything already built: the route planner's polyline and per-leg labels appear on it, as do the connection arrows and the foreground masks.

## Sketch

1. **Parameterise the renderer.** `draw()` in [js/render.js](../public/js/render.js) uses the module-level `ctx`/`cv` and reads `state.cam` directly. Extract the body into `paint(ctx, cam, width, height, dpr)` and reduce `draw()` to a call with the live values. Mechanical.
2. **Preload the artwork.** `img()` is lazy and `draw()` skips images that are not `complete` — fine for an interactive canvas that repaints, fatal for a one-shot export, where you would silently get holes. Add a helper that resolves when every `png` (and `fg`, if `show.fg`) of `path.cams` has loaded, and await it before painting. Same for `tintedImg`, which returns `null` until its source is loaded.
3. **Paint and download.** Create the offscreen canvas at full path size, paint at `z = 1`, `toBlob`, reuse the download helper with [49](item-049-png-export-revoke-race.md)'s deferred revoke.
4. **UI.** Two buttons — "Export view" and "Export whole path" — is the clearest and avoids a mode.

## Watch out — canvas size limits, the real constraint

Largest paths, measured from the shipped data:

| path | cells | pixels | megapixels | RGBA backing store | cams |
| --- | --- | --- | --- | --- | --- |
| AE MI P4 | 12×14 | 4416×3360 | 14.8 | 59 MB | 37 |
| AE MI P1 | 15×9 | 5520×2160 | 11.9 | 48 MB | 31 |
| AE BA P5 | 13×10 | 4784×2400 | 11.5 | 46 MB | 24 |
| median path | — | — | 1.8 | 7 MB | — |

The median is trivial; the tail is not. Historical iOS Safari caps canvas area near 16.8 MP **and** a single dimension at 4096 px — AE MI P1 is 5520 px wide and would fail there. Modern Safari has raised both, but this must be tested on a real device. Design for the failure: compute the target size, and if it exceeds a configured budget, scale down to fit and say so in a toast rather than downloading a blank image. `toBlob` calling back with `null` is the existing signal that this happened.

**Label sizes are zoom-relative.** Every font and line width in `paint` is divided by `cam.z` so it stays constant in *screen* pixels. At `z = 1` on a 4416 px-wide image, an 11 px object label is nearly invisible. Decide deliberately: pass an explicit label scale for the export path, or accept small labels as correct-at-1:1. Recommendation: a `labelScale` defaulting to 1, set to ~2 for export. Do not "fix" it by exporting at `z = 2` — that doubles the memory and interpolates the artwork.

**`imageSmoothingEnabled`** is set from `cam.z < 1`; at `z = 1` it is off, which is right for pixel-exact art. Confirm rather than assume after the refactor.

**Transient overlays must not render.** `flash` and `highlight` are hover and navigation affordances and would bake a stray ring or dashed outline into a shared image. Skip both in the export paint. The route and ruler *should* render — the route is promised in the README, and the ruler is a deliberate annotation.

**Filename.** Distinguish the two exports so a folder of them is intelligible.

**File size.** A 15 MP PNG of photographic-ish MDEC art will land in the multi-megabyte range. Fine for an explicit download, but disable the button and show a toast while it runs.

## Verify

Export AO R1 P15 and confirm 4416×720 with all 20 screens present and no missing tiles — that is what the preload step is being tested for. Export AE MI P4 on desktop Chrome, Firefox, Safari and a real iPhone, and record what actually happens on iOS in the commit message. Toggle collision, foreground and connection arrows on and re-export. Plot a route and confirm it and its leg labels appear.

## Ships with

README and a `changelog.json` entry, tag `new`.
