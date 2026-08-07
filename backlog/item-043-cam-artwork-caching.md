# 43. Cam artwork caching

**Status:** shipped 2026-07-19 · **Effort:** medium · **Where:** anywhere, viewer-only

Never filed as an idea before it was built — it came out of a performance problem rather than out of the backlog, and took its number afterwards.

## What and why

GitHub Pages re-stamps its HTTP validators on every deploy, so ordinary browser caching re-downloaded every screen the visitor had already seen. For a site whose artwork is 195 MB, that is the difference between a repeat visit rendering instantly and paying for the whole level again.

## Decided

**Opt-in, off by default.** Filling a visitor's storage with artwork is not something to do without being asked.

**A versioned Cache API bucket, cache-first**, capped at 2000 entries with a FIFO trim, so the store cannot grow without bound.

**`settings.js` owns registration**, and disabling deletes the buckets rather than merely stopping — an opt-out that left the data behind would not be an opt-out.

## Shipped

[sw.js](../public/sw.js) serves `cams/**/*.png` cache-first, gated on the "Cache screen artwork on this device" setting.

**The standing obligation this created** — bump `CACHE_NAME` whenever cam artwork is regenerated, or opted-in visitors keep the old art forever — is retired: [54](item-054-stamp-cache-name.md) has the builder stamp the name from a content hash of the artwork, on the grounds that three documents describing a manual step is the signature of a missing mechanism.
