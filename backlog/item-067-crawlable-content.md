# 67. Crawlable content for search engines

**Status:** shipped 2026-09-01 · **Effort:** medium (site, product) · **Where:** anywhere; no disc · **Filed:** 2026-07-24/25 review

## What it is

`sitemap.xml` contains exactly one URL, and the site renders entirely client-side from JSON. So a search for "Oddworld Paramonia map" or "Scrabanian Temple layout" has nothing to land on except the root, and the site's actual depth (191 paths, 16,225 catalogued objects, 1,761 screens, measured 2026-08-26) is invisible to indexing.

A generated static index — one lightweight HTML page per level, or one page listing every path with its permalink and object counts, linked from the root and listed in the sitemap — would make that depth findable, and each page would deep-link into the real viewer. The builder already has every fact needed to emit it.

## The decision to make

This is a growth feature with a real maintenance surface: generated HTML in the repo, another thing the builder emits, another thing to keep in sync. It only matters if discovery via search is a goal. If the site grows mainly through community links and embeds, skip it.

Worth an explicit yes or no rather than drift — and note it interacts with [65](item-065-trim-pages-deploy.md), since it means more files at the site root.

## Shipped

Yes: strangers finding a place by name is an audience worth serving. Every level has a page under `/levels/` — 25 of them and an index, with `sitemap.xml` grown from one URL to 27 — and each is a real content page: the level's counts, a screen of its way in, and its paths in play order, every one an ordinary link into the viewer's own `#GAME/LEVEL/PATH` address. A redirecting stub was the tempting shape and was dropped: a crawler indexes a redirect's destination with the fragment cut off, so every stub would have collapsed into the homepage this item exists to escape.

The sketch's "builder emits it" landed as `tools/levelpages.js`, a Node emitter, because nothing here needs a disc: the inputs are the two committed data files and `annotations.json`, and the names, play order and demo exclusion already exist as the viewer's own bare-Node modules — a page composes the same label the path button shows, from the same function. The output is committed like the rest of the generated site data, and `tests/unit/levelpages.test.js` byte-compares it against a fresh emit on every CI run — the fully-reproducible position [64](item-064-sidecar-reemit-check.md)'s enum half still cannot reach — so an `annotations.json` edit or a data rebuild now owes a re-emit in the same commit, and CI is what remembers.

The pages sit nested under `/levels/` rather than "at the site root" as filed: the service worker's shell rule takes an HTML page only at the site root, so nesting is what keeps a level page out of the offline story without touching the worker at all.
