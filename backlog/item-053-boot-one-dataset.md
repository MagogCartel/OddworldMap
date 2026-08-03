# 53. Boot on one dataset, hydrate the other

**Status:** open · **Effort:** small-medium (viewer, performance) · **Where:** anywhere, viewer-only · **Filed:** 2026-07-24/25 review

## Symptom

[js/main.js](../public/js/main.js) `Promise.all`s seven files before anything is drawn. Measured payloads at the review:

| file | raw | gzip |
| --- | --- | --- |
| `map_data_ao.json` | 2.12 MB | 172 KB |
| `map_data_ae.json` | 4.74 MB | 345 KB |
| the five sidecars combined | 46 KB | 7.8 KB |

So first paint waits on **~517 KB gzipped / 6.9 MB raw**, and the visitor is looking at one game. On 4G that is roughly a three-second blank canvas where it could be one.

## Sketch

Decide the boot game *before* awaiting, then await only it.

1. Parse `location.hash` (`parseHash` is already pure and importable) and, failing that, `storedLocationHash()`, to get a target game id. Fall back to AO.
2. `await` that dataset plus the sidecars, which are tiny, then run the existing `initGames`/`resize`/`applyHash` sequence with a one-element `games` array.
3. When the second dataset resolves, push it into `state.games`, append its game button via the existing `initGames` loop, and re-run an active search.

## Watch out

**`initGames` is currently once-only.** [js/navigate.js](../public/js/navigate.js) assigns `state.games = games` and appends buttons. Make it additive, or split an `addGame(G)` out of it. `markOn` uses `dataset.key`, so a later-appended button highlights correctly with no change.

**Search assumes both games are loaded.** `runSearch` iterates `state.games`, the group scaffolding builds a group per game up front, and the summary line prints a per-game hit count. With one game loaded these silently narrow. Re-run an active search when the second dataset lands, and consider a note in the summary while it is still in flight. This is the part that will feel broken if skipped — a user who searches in the first 800 ms gets AO-only results with no indication.

**A hash naming the un-booted game.** If the URL is `#AE/MI/1/…`, AE *is* the boot dataset by step 1, so that resolves itself. But `applyHash` also runs from the `hashchange` listener — paste an AE link while only AO is loaded and `state.games.find` returns undefined, so the hash is silently rejected. Guard it: if the hash names a known-but-unloaded game, await it first. Keep a module-level promise per game so this is an await, not a second fetch.

**The preloads compete.** [index.html](../public/index.html) preloads both datasets. Leaving both means the AE download contends with the AO one on the critical path, undoing much of the win on slow links. Add `fetchpriority="low"` to the second, or make it conditional. Do not simply delete them — they exist to start the download during HTML parse rather than after the module graph resolves.

**`loadOne` swallows failures**, returning `null` on any error. Today a total failure is caught by the "Map data failed to load" branch. With a lazy second dataset, a failed AE fetch must not leave a dead AE button in the sidebar — either do not append the button until the data lands, which is the recommendation, or mark it disabled.

## Verify

DevTools → Network → throttle to "Slow 4G", hard reload with an empty hash: the map must draw after ~172 KB, not ~517 KB. Then confirm the AE button appears a moment later, an AE permalink pasted while on AO resolves, and a search typed during the gap re-runs and picks up AE hits.

## Ships with

A `changelog.json` entry, tag `improved` — this one is squarely user-visible.
