# 83. Offline app shell

**Status:** open · **Effort:** small-medium (sw.js, settings) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

The opt-in service worker ([43](item-043-cam-artwork-caching.md)) keeps visited artwork, so a returning visitor re-downloads no screens — but with no network at all the site still dies at the front door: `index.html`, the modules, the stylesheet and the data JSONs are never cached. The artwork cache is 95% of an offline map that falls at the last 5%. "The map works on a plane" costs roughly 7 MB more, and only for visitors already opted in.

## Sketch

- Behind the same `cacheImages` setting (it becomes "keep the map on this device", copy updated): on enable, the worker precaches the shell — `index.html`, `css/main.css`, `js/*`, the two `map_data` files and the six sidecar JSONs — into a versioned `shell-…` bucket, and serves them cache-first with a background revalidate (the JSONs currently rely on `no-cache` revalidation; stale-while-revalidate keeps updates flowing while surviving offline).
- The versioning discipline is the artwork cache's, whose name the builder now stamps as a content hash of the cams ([54](item-054-stamp-cache-name.md)) — but the shell cannot ride that hash, which holds still when only the app changes. The shell bucket wants its own stamp, derived from the shell files the same way, or it serves last month's app forever.
- Disable keeps its existing meaning: delete every bucket, unregister.

## Watch out

- The worker cannot read settings ([43](item-043-cam-artwork-caching.md)'s marker-bucket dance exists for exactly this); the shell bucket needs the same enable/disable choreography.
- Update lifecycle: a cache-first `index.html` plus a waiting worker is the classic two-reloads-behind trap. Decide `skipWaiting`/`clients.claim` behaviour deliberately and write it down.
- Whole-map prefetch ("download a level for the flight") is a different, larger feature; this item is only the shell.
