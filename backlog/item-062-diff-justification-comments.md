# 62. Sweep the codebase for diff-justification comments

**Status:** open · **Effort:** small (cleanup) · **Where:** anywhere · **Filed:** 2026-07-24/25 review

## Symptom

[CLAUDE.md](../CLAUDE.md)'s code-comment convention forbids comments that explain *how the code got here* rather than what constrains it — "no inter-diff comments", and "peer items get peer prose": if your addition carries a defence its siblings lack, delete the defence. The convention was written after most of the code, and nothing has checked the existing tree against it. Two were found and cut while building [58](item-058-restore-pinch-zoom.md), both by the same tell — the commented line was the one just added, and its siblings were bare.

## The tell to search for

This cannot be grepped directly. It is a comment whose sentence would stop making sense to someone who never saw the previous version of the file. In practice they read as a defence of a line's existence ("without this, X would happen") sitting among uncommented peers that do equally non-obvious things, or as a narration of a move ("extracted from", "now lives here", "was previously"). The reliable question is the convention's own: would the prose look the same if every line in the block had been written on the same day, by one author?

## Sketch

A read-through of `js/` and `tools/` comment by comment, one commit per file or per cluster, deleting only. Keep anything recording a durable why: an invariant, a browser or format constraint, a trade-off, a value the code cannot show. When a comment is genuinely load-bearing but framed as history, reframe it as a present-tense constraint rather than deleting it.

## Watch out

**This is a judgement sweep, not a mechanical one, and deleting a real constraint costs more than leaving a stale justification.** When unsure, leave it. The high-value targets are the files that grew by accretion across many features — `interaction.js`, `render.js`, `navigate.js`, `search.js`, `build_map.py` — not the leaves, which were mostly written in one pass.

Do not bundle this with any behaviour change; a comments-only diff is reviewable at a glance and a mixed one is not. Unlike the Prettier and README reformats, this does **not** belong in `.git-blame-ignore-revs` — deleting a comment is an authorship decision, and blame should record it.

## Ships with

Nothing — internal. No changelog entry.
