# 70. Dropping the numeric `t` and empty `extra` from map_data

**Status:** closed — rejected, recorded so it is not re-proposed · **Effort:** n/a · **Where:** n/a · **Filed:** 2026-07-24/25 review

## What was proposed

The review noted that `t`, the numeric TLV type id, is shipped on all 16,217 objects and read by neither the viewer nor the tests, and that `"extra": {}` appears on 14,698 of them. Removing both saves 0.55 MB raw but only ~18 KB gzipped.

## Rejected

`map_data` is a data contract and completeness matters more than 18 KB; the numeric id may be used later.

**Also explicitly decided: do not document it as unused.** That would signal it is safe to remove. No action.
