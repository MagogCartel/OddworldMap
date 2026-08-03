# 69. Browser-level smoke tests

**Status:** deferred — "true, but it's getting a lot to test" · **Effort:** medium (CI) · **Where:** CI · **Filed:** 2026-07-24/25 review

Recorded in full because the reasoning may change, and because [57](item-057-module-lifecycle.md) would be materially safer with it.

## The gap

`render`, `interaction`, `navigate`, `search`, `sidebar`, `campanel`, `fieldpanel`, `route`, `whatsnew`, `dialog` — roughly 2,000 lines — have ESLint as their only pre-runtime check. [CLAUDE.md](../CLAUDE.md) states the risk plainly: there is no JS build step, the modules are served as-is, so lint is the only pre-runtime error check. A stale reference or a broken listener wiring is a production bug that nothing catches.

## Why it is smaller than it looks

The point is not coverage; it is a handful of assertions that would have caught real regressions. Playwright against `python3 -m http.server`, one CI job:

1. Boot with an empty hash: the canvas is non-blank (sample a few pixels) and no console errors.
2. Permalink round-trip: load `#AO/R1/15/…`, read `location.hash` after settle, assert it matches.
3. Follow: click a known door at known coordinates, assert the resulting level and path.
4. `?embed=1`: `.chrome` elements hidden, the open-site button visible.
5. Search: type `lcdstatusboard`, press Enter, assert the view moved and the hash changed.
6. Settings persistence: toggle one, reload, assert it stuck.

That is an afternoon, and it would cover the boot path, the permalink grammar, the follow logic, embed mode and settings — the five things that break in ways users notice immediately.

## If it is ever picked up

Do it *before* [57](item-057-module-lifecycle.md), and fold [63](item-063-alignment-anchor-diff.md) in as a seventh test.
