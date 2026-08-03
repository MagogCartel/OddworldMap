# 10. Embed mode

**Status:** shipped 2026-07-19 · **Effort:** small · **Where:** anywhere, viewer-only

## What and why

Wikis and forum threads want the map inside the page, and the full site's furniture — What's New, the copy-link button — belongs to the site rather than to the map.

## Decided

**Hide by class, not by enumeration.** `?embed=1` hides whatever carries `.chrome`, so a new piece of site furniture opts out of embeds by wearing the class rather than by being added to a list.

**The sidebar starts closed but stays reachable.** An embed with no level buttons at all would be a picture; one that opens them on demand is still the map.

**An embed neither reads nor writes the remembered location.** Someone else's page should not inherit, or overwrite, where this visitor last was on the full site.

## Shipped

`?embed=1`, plus an embed-only corner link that opens the full site at the exact current view.
