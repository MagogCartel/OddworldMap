# 63. Automate the alignment anchors as a screenshot diff

**Status:** undecided — needs a decision before anyone builds it · **Effort:** medium (CI) · **Where:** CI · **Filed:** 2026-07-24/25 review

## What it is

[CLAUDE.md](../CLAUDE.md) records two manual eyeball checks for catching a world-to-art transform regression: *AO R2 P1 C03 — the LCDStatusBoard box sits on the LED digit panel of the Employees sign*, and *AE MI P1 C24 — the HandStone box sits on the QuikSave stone*, with the tell being "if object markers drift toward screen centers, a world-to-art transform regressed".

That is a screenshot-diff test written in prose. Two fixed permalinks, two committed reference PNGs, a headless browser, a pixel-delta threshold. It converts the single most expensive and most forgettable manual verification in the project into a gate.

## The decision to make

It costs a headless-browser dependency in CI and two reference images in a repo that is already large — they would be small, a 400×300 crop each. It also overlaps [69](item-069-browser-smoke-tests.md): if browser tests ever land, this is one of them and should not be built as a separate mechanism.

**Recommendation: fold it into 69 rather than building it standalone**, unless 69 stays deferred indefinitely, in which case this narrow version is worth it on its own — it is the highest-value single assertion in the whole test surface, because the failure it catches is silent, global and visual.
