# 55. Lint and test `tools/` in CI

**Status:** shipped 2026-07-26 · **Effort:** small (CI) · **Where:** anywhere — the tests need no disc · **Filed:** 2026-07-24/25 review

## Symptom

The `tools/` tree had **zero** automated coverage of any kind. ESLint ignored it, Prettier ignored it, and the CI workflow never invoked Python. A syntax error, a bad import or a broken regex in the 1,260-line builder was discovered only on the next disc-machine session — which is the scarce resource this project schedules around.

## Why it matters more than the line count suggests

The builder is the only thing that can produce the site's data, and it depends on regex-parsing a third-party C++ codebase that moves upstream. The parsers are exactly the code most likely to break silently and least likely to be exercised casually.

## Sketch, in two commits

*Commit 1 — static checks.* Add a Python job to [.github/workflows/ci.yml](../.github/workflows/ci.yml) running `compileall` and `ruff`. `compileall` alone catches the syntax class for free.

*Commit 2 — unit tests.* Add `tools/tests/`. The high-value targets are the pure functions with tricky, hard-won logic and no coverage: `_match_brace`, `_derive_label`, `_strip_comments` (the "an `enum` inside a comment swallows the definition that follows" trap and the phantom-enumerator-from-a-comma bug — both recorded in prose and pinned by a JS test on the *output*, where a Python test would pin the *cause*), `int_rows` / `positional_rows`, `parse_chunks` (feed it a truncated buffer and assert it terminates), `decompress_4or5`, `object_fields`' payload clamp, and `write_field_types`' stale-override guard.

None of these need a disc or an `alive_reversing` checkout, which is what makes them CI-able. Do **not** try to test the disc/LVL/CAM path — that needs the images and belongs on the disc machine.

## Watch out

Keep the fixtures inline in the test file — small byte strings, small C++ snippets — rather than adding binary fixtures to a repo already carrying 182 MB of `.git`.

Adding Python tests must not drag `tools/` into the Prettier or ESLint globs; check `npm run format:check` still passes after the tests land.

## Found while doing it

Three things the sketch predates. **Ruff's default selection is no longer just the defect rules** — 0.16 flags the parsers' one-line `if`s, `re.S` aliases and `l` as a name, all deliberate style — so `ruff.toml` selects `E4,E9,F` and the version is pinned in CI the way Prettier's is. **The 3.8 floor cannot be checked in CI at all**: it is EOL and gone from the runner images, so only a modern version runs there and the floor is a local check. And **`positional_rows`, along with the enum value/label loop, is nested inside its parser and unreachable from a test** — that coverage waits on hoisting them, which the package split ([56](item-056-split-build-map.md)) moved past without doing: a nested helper is out of reach whatever file it sits in.

Tests are stdlib `unittest`, not pytest, so the suite needs no install step on the runner or the disc machine.

## Worth more than the unit tests

`write_field_types` and `write_enum_labels` can be re-emitted into a temp dir and compared byte-for-byte with the committed sidecars, which pins every parser behind them at once. The field-types pair needs only the committed caches, so it runs in CI; the enum-label pair needs the decomp checkout and skips without one.

## Ships with

Nothing user-facing. A short "Dev tooling" line in the README, since it claimed `npm run lint` and `npm test` were the only dev tooling — that sentence became wrong and had to be updated in the same commit.
