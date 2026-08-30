# 66. Add a `404.html`

**Status:** shipped 2026-08-30 · **Effort:** tiny (site) · **Where:** anywhere · **Filed:** 2026-07-24/25 review

## What it is

Without one, GitHub Pages serves its default 404. Since the app is hash-routed, any 404 means a genuinely missing file — a stale link to a moved asset, or a mistyped path. A branded 404 with a link back to the map is a few lines and costs nothing.

## The decision to make

Worth the file, or noise? No strong opinion; it is the kind of thing that is nice to have and never urgent.

## Shipped

Worth the file. `public/404.html` is a page on the site's palette — the Mudokon mark, *This screen isn't on the map*, and the link back — with no script and no stylesheet: a page about a missing file depends on nothing that could itself be the missing file. Every URL on it is root-absolute, because Pages serves the file at whatever missing address was asked, and a relative URL would resolve against that address. It carries `noindex`: the missing addresses answer at status 404, which no engine indexes, but a direct visit to `/404.html` is a 200 that a shared link could get indexed.

Nothing else moved. The deploy uploads `public/` whole, so the file ships by landing there; the page stays out of `sitemap.xml`, having no address of its own worth naming; and the service worker needed no change — whichever of its branches a missing address falls into, an error response is never stored, so any 404 a visitor meets is the network's own, and the stock-versus-branded question was Pages' alone to answer.
