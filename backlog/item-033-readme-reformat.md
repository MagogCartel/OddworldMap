# 33. Reformat and de-blob the README

**Status:** shipped 2026-07-27 · **Effort:** small (docs, formatting first) · **Where:** anywhere

## What and why

Feature growth kept *appending clauses to the same existing bullets* — the Settings bullet worst of all, where `git blame` showed change after change piling onto one line. The diffs had become near-unreadable and painful to rebase.

## Sketch

Reformat the offending bullets into nested sub-bullets and shorter lines — **no wording changes, pure structure** — in a dedicated commit, and add that commit to `.git-blame-ignore-revs` so blame still credits whoever wrote each clause rather than the reformat. The same discipline CLAUDE.md's Prettier note describes.

## Decided

**The order was the point, and it is why this is two commits rather than one.** The structural pass carries no wording changes and is blame-ignored; the editing pass that follows is an ordinary commit blame should keep. Bundling them would have forced a choice between losing the authorship of every clause and losing blame for the real edits.

## Shipped

*Break the README's blob bullets into nested sub-bullets* (`8b3f2bb`) split the blobs with no wording changes and went into `.git-blame-ignore-revs`; *Lead the README with orientation, group the reference detail* (`e47002b`) then did the real editing as an ordinary commit.

Two follow-ups rode along: *Document the two Display toggles and the export button* (`24c249e`) covered three features the reformat exposed as undocumented, and *Normalize sub-bullet capitalization under Controls* (`8de1f02`) was blame-ignored too (`75607ee`).

Landed before [60](item-060-search-place-names.md) and [61](item-061-export-whole-path.md), whose docs land in exactly these bullets — which was the scheduling reason to do it when it was done rather than later.
