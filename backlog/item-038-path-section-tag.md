# 38. Separate a path's section tag from its name

**Status:** shipped 2026-07-29 · **Effort:** small (builder + rebuild) · **Where:** disc machine (AE rebuild)

## What and why

`map_data` put two different things in a path's `name`. For AO's Rupture Farms Return it is a genuine per-path label the game itself uses — the save slots read "Rescue Zulag N". For AE's thirteen ender paths it was the *level display name* of the endgame half, stamped on by the builder because the path is only ever referenced under an ender id: "Mudanchee Vault Ender" is not what that room is called, it is which half of the level it sits in.

The override rule could not tell them apart, so thirteen curated names had to swallow the tag and led with developer jargon.

## Decided

**The rule was right; the data was the defect.** Keeping a curated name from quietly contradicting the game is what settled the zulag 13/14 question rather than papering over it.

**Rendered where there is room to explain it:** a dim line under the level in the place panel, and leading the path button's tooltip. Deliberately *not* on the chip or the button label — those are the surfaces the split shortens.

## Findings

**The override rule needed no weakening at all.** It is conditional on the path having a disc name, so it simply stops applying to Exoddus while still guarding Oddysee's eighteen. That is the evidence the split cut where the defect actually was: a fix that needs the rule relaxed would have been cutting somewhere else.

Verified over the shipped data, 2026-07-29: all thirteen ender paths carry `section` and none keeps `name`, AO's eighteen are untouched, and no path has both (pinned as an assertion, not a count). Shortening created no in-level name collisions in either game, which was the real risk once the qualifier came off. The longest chip label fell from 48 characters to 30, which moved CLAUDE.md's geometry anchor to AE `BA P4`.

AE-only rebuild: the data diff is exactly thirteen `"name"` → `"section"` lines, the sidecars byte-unchanged, AO untouched.
