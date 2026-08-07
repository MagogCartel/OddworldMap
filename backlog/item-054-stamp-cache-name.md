# 54. Stamp `sw.js`'s `CACHE_NAME` from the builder

**Status:** shipped 2026-08-07 · **Effort:** small (builder + docs) · **Where:** builder; verifying the bump needs a rebuild · **Filed:** 2026-07-24/25 review

## Symptom

[sw.js](../public/sw.js)'s `const CACHE_NAME = "cams-v1"` must be bumped by hand whenever any cam PNG is regenerated. Both [CLAUDE.md](../CLAUDE.md) and [README.md](../README.md) document the obligation, and [43](item-043-cam-artwork-caching.md) repeats it a third time. The failure mode is silent and unobservable from the maintainer's own machine: opted-in visitors serve the old artwork cache-first and never revalidate, so they keep stale art indefinitely while everything looks correct locally.

## Why this is the right fix

Three documents describing a manual step is the signature of a missing mechanism. The builder already knows exactly when it wrote a PNG — `cam_stats["decoded"]` in [tools/build_map.py](../tools/build_map.py) — so the information needed to bump the constant is in hand at the moment it becomes necessary.

## Sketch

In the builder, after the cam loop:

1. Compute a stamp over the emitted artwork. A hash of the sorted `(relative path, size, mtime)` tuples is *not* deterministic enough — use a hash of the sorted `(relative path, sha1-of-bytes)` list for the `cams/<game>/` tree. 2,846 files is a few seconds, the build is already minutes long, and byte-determinism is a stated property of this pipeline, so a content hash is stable across rebuilds that change nothing.
2. Rewrite the `CACHE_NAME` line in place with a narrow regex.
3. Print it in the build summary next to the `data file` row.

Because both games share one service worker, the stamp must cover `cams/ao` **and** `cams/ae`, not just the game being built. A subset build must therefore still hash the whole tree — cheap, and it keeps the invariant true.

## Watch out

**The ordering trap.** A subset build merges into the existing data file and existing PNGs are skipped for speed, so a build that decodes nothing must leave `CACHE_NAME` unchanged. Hashing the tree rather than counting decodes gives that for free — the reason to prefer the content hash over `if cam_stats["decoded"]`.

`sw.js` is linted as a `serviceworker`-globals script and Prettier-formatted. The rewritten line must survive `npm run format:check`; keep the exact quoting and semicolon.

**Do not stamp on every build.** If the hash is unchanged, do not rewrite the file at all — no mtime churn, no accidental staged diff.

## Then remove the manual instruction

This is the point of the change: in the same commit, delete the "bump `CACHE_NAME`" sentence from CLAUDE.md and README.md and replace it with a note that the builder stamps it. Leaving the manual instruction in place next to the automation is worse than either alone. [43](item-043-cam-artwork-caching.md) records the obligation as the standing cost of that feature, so it wants the same edit.

## The loop the stamp alone leaves open

A check that `sw.js`'s stamp matches the committed `cams/` tree was first dismissed here as only mattering for a hand-edited PNG, which nothing plausible does. That weighed the wrong risk. The likelier slip is a **partial commit** — artwork staged, `sw.js` not — which the per-concern staging this repo prescribes makes easy to do, and which the builder cannot catch because it has already done its part correctly. So the check landed after all: `cams_stamp` over `public/cams` against the committed line, no disc and no decomp, well under a second, in `tools/tests` with the rest.

## Shipped

`stamp_cache_name` hashes `public/cams` — every PNG's path and the sha1 of its bytes, sorted — and rewrites the one `CACHE_NAME` line, only when the hash moved. The name is `cams-` plus twelve hex digits, so the worker's `startsWith("cams-")` cleanup still collects the bucket it replaces and still spares the `cams-on` marker.

Two guards the sketch did not ask for. The rewrite fails the build when it finds no line of that exact shape, since silently stamping nothing is the failure this item exists to kill; and a scratch `--out` holds no `sw.js`, so a verification build stamps nothing and stays side-effect-free. Hashing 2,846 files costs well under a second — the sketch budgeted seconds.

Measured 2026-08-07: the committed tree stamps `cams-520477b56197`. Re-running the same build, building the other game, and a `--levels R2` subset all reproduce it and leave `sw.js` untouched; changing one byte of one PNG moves it to `cams-fa4e46304413` and restoring the byte returns it, which is the content-addressing the ordering trap needs. Unit tests cover the bytes-and-path sensitivity, the single-line rewrite and the loud failure.

## Verify

Rebuild one level on the disc machine, confirm `sw.js` changed and the new name appears in the summary. Rebuild again with nothing to decode, confirm `sw.js` is untouched. In a browser with caching enabled, confirm the old `cams-*` bucket is deleted on activate and the new one fills.

## Ships with

README and CLAUDE.md edits in the same commit — mandatory, since they currently document the removed obligation. No changelog entry: players cannot perceive it, and the changelog explicitly excludes tooling.
