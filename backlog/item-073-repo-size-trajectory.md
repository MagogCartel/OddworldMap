# 73. Repo and artwork size trajectory

**Status:** closed — recorded only so the number is not mistaken for an unmanaged risk · **Effort:** n/a · **Where:** n/a · **Filed:** 2026-07-24/25 review

## What was flagged

That `.git` is 182 MB against 195 MB of committed artwork, and that a future full art regeneration would add another ~195 MB permanently.

## Closed

No further artwork rewrite is planned — the art is considered final and is already maximally compressed by oxipng, 288 MB down to 195 MB (the [backlog README](README.md)'s *Shipped without a file* entry for PNG optimization records that figure's origin).

The one previous rewrite was done by deleting and recreating the GitHub repo, so history carries no orphaned pre-optimisation blobs and the current size is the floor. Nothing to plan for.
