# 67. Crawlable content for search engines

**Status:** undecided — needs a decision before anyone builds it · **Effort:** medium (site, product) · **Where:** builder emits it; no disc · **Filed:** 2026-07-24/25 review

## What it is

`sitemap.xml` contains exactly one URL, and the site renders entirely client-side from JSON. So a search for "Oddworld Paramonia map" or "Scrabanian Temple layout" has nothing to land on except the root, and the site's actual depth — 190 paths, 16,217 catalogued objects, ~2,850 screens — is invisible to indexing.

A generated static index — one lightweight HTML page per level, or one page listing every path with its permalink and object counts, linked from the root and listed in the sitemap — would make that depth findable, and each page would deep-link into the real viewer. The builder already has every fact needed to emit it.

## The decision to make

This is a growth feature with a real maintenance surface: generated HTML in the repo, another thing the builder emits, another thing to keep in sync. It only matters if discovery via search is a goal. If the site grows mainly through community links and embeds, skip it.

Worth an explicit yes or no rather than drift — and note it interacts with [65](item-065-trim-pages-deploy.md), since it means more files at the site root.
