# 69. Browser-level smoke tests

**Status:** shipped 2026-09-02 · **Effort:** medium (CI) · **Where:** CI · **Filed:** 2026-07-24/25 review

Recorded in full because the reasoning may change, and because [57](item-057-module-lifecycle.md) would be materially safer with it.

## The gap

`render`, `interaction`, `navigate`, `search`, `sidebar`, `campanel`, `fieldpanel`, `route`, `whatsnew`, `dialog` (3,008 lines, and 4,603 across every module the DOM-free suite cannot reach, measured 2026-08-26) have ESLint as their only pre-runtime check. [CLAUDE.md](../CLAUDE.md) states the risk plainly: there is no JS build step, the modules are served as-is, so lint is the only pre-runtime error check. A stale reference or a broken listener wiring is a production bug that nothing catches.

## Why it is smaller than it looks

The point is not coverage; it is a handful of assertions that would have caught real regressions. Playwright against `python3 -m http.server`, one CI job:

1. Boot with an empty hash: the canvas is non-blank (sample a few pixels) and no console errors.
2. Permalink round-trip: load `#AO/R1/15/…`, read `location.hash` after settle, assert it matches.
3. Follow: click a known door at known coordinates, assert the resulting level and path.
4. `?embed=1`: `.chrome` elements hidden, the open-site button visible.
5. Search: type `lcdstatusboard`, press Enter, assert the view moved and the hash changed.
6. Settings persistence: toggle one, reload, assert it stuck.

That is an afternoon, and it would cover the boot path, the permalink grammar, the follow logic, embed mode, search and settings — the six things that break in ways users notice immediately.

## If it is ever picked up

Do it *before* [57](item-057-module-lifecycle.md), and fold [63](item-063-alignment-anchor-diff.md) in as a seventh test.

## Shipped

All six assertions, in `tests/browser/smoke.spec.js`, on the harness [63](item-063-alignment-anchor-diff.md) brought — before [57](item-057-module-lifecycle.md), as the note above asked, with 63 folded in as its own spec rather than a seventh test.

Two of the sketch's tests drifted on contact with the shipped behaviour. The permalink round-trip cannot assert `location.hash` survived, because a plain view hash is never rewritten at all — it asserts the live `viewHash()` reproduces the loaded string, a real parse→apply→format round trip, on a coordinate chosen window-interior so the world→draw conversion is exact both ways. And the search test's Enter jumps to a plain view hash rather than anything naming the object, so "the view moved and the hash changed" is asserted exactly as written here and no tighter. The follow-click's "known coordinates" are computed from the live modules at run time (`markerCentre` through the camera transform), never hard-coded screen pixels; the door is pinned by name and world rect like an anchor — AO R1 P15's one followable at that spot, through to R1 P16.
