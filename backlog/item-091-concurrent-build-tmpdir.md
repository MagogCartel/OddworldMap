# 91. Two builds in one checkout corrupt each other's artwork

**Status:** shipped 2026-08-28 · **Effort:** small (builder) · **Where:** anywhere; reproducing it needs the discs · **Filed:** 2026-08-28, out of [56](item-056-split-build-map.md)'s verification

## Symptom

`main()` hands `decode_cam` a scratch directory fixed at `tools/.tmp`, and `decode_cam` writes `cam.bits` and `cam.rgba` into it under those names for every camera of every build. Nothing in the path varies by run, by game or by level, so two builds in the same checkout share both files: one writes `cam.bits` while the other's `cam2rgba` is reading it, and a PNG comes out carrying another camera's pixels.

It fails silently. The image is the right size and the right shape, the decode reports success, oxipng compresses it happily, and the build summary counts it decoded. Only a byte comparison against a known-good tree finds it.

## Measured

2026-08-28, two full `--game AO` builds started together into separate `--out` trees: one of the 110 PNGs the shorter run had written differed from the committed artwork, the other run's 935 were clean. The same collision hit a review of [56](item-056-split-build-map.md) from a second direction, an agent running the builder while a verification build was in flight, which is how it was noticed at all.

Reproduce by running two builds at once and comparing each tree against `public/cams`; expect a handful of files at most, since the window is one subprocess call wide.

## Why it matters more than the odds suggest

`--out` exists so a build can be checked against the committed tree without touching it, which is exactly the workflow that invites a second build alongside the first. The pipeline's whole guarantee is that it is byte-deterministic, and this is the one way it is not: a corrupted PNG is indistinguishable from a good one until something diffs it, and committing one would poison the artwork and the `sw.js` cache stamp together.

## Sketch

Give each build its own scratch directory rather than each camera its own filename: `tempfile.mkdtemp()` at the top of `main()`, removed at the end. That also retires the `tools/.tmp` directory, which is currently created in the source tree and left behind.

Per-camera unique names inside the shared directory would close the same race, but they leave the litter and still let two builds fill one directory.

## Watch out

The temp files are handed to `cam2rgba` as a path on its command line, so the directory has to outlive the subprocess; a `TemporaryDirectory` context around the build loop is the shape, not one per camera.

`decode_cam` is in `oddmap/image.py` and takes the directory as a parameter already, so nothing about the fix reaches into it.

## Shipped 2026-08-28

A `TemporaryDirectory` per run in `main()`, cleaned up at the end, in place of the fixed `tools/.tmp`. `decode_cam` already took the directory as a parameter, so nothing inside it changed and the per-camera filenames stayed as they were: giving each build its own directory is what the collision needed, not giving each camera its own name.

The check is the reproduction. Two full `--game AO` builds started together, which produced a corrupted PNG before, now give 935 files each and every one matches the committed artwork.

It retires three `.gitignore` entries with it, the source tree no longer being where a build puts its intermediates: `tools/.tmp`, and the `*.rgba` / `*.bits` globs whose only ever matches were the two files `decode_cam` writes. `tools/cam2rgba` stays, the compiled binary still landing there.

**The sketch asked for a `with` block and the ship did not use one.** A context manager around the build loop would re-indent 150 lines of `main()` for a scope that is already the whole function; an explicit `cleanup()` at the end reads the same and leaks nothing, since the finalizer removes the directory on any path out that skips the call.
