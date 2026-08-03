# 37. Per-path notes

**Status:** retired 2026-07-30 — the plumbing and the notes shipped; the content pass was retired rather than completed · **Effort:** small (viewer) plus open-ended curation · **Where:** anywhere, viewer data only

## What and why

A curated name says what a place is called. A note says what is odd about it — the zulag whose signage contradicts itself, the secret area built from another level's artwork — which is the kind of thing a reader comes to a map like this for.

## Decided

**What a note is for — keep it narrow, or it rots.** A note is a short player-facing curiosity about *that* path: one or two sentences, the sort of thing you would say out loud pointing at the screen. The test is whether a player who already knows where they are would still find it interesting.

**It is not the evidence trail for the name.** Why `FD P3` is Terminal 3 is a note — "the one terminal the game never numbers". *How* that was established is not; that belongs in the commit that curated it.

**A note-only entry is legal for a path but not for a level.** A path always has a disc name to hang a note on; forcing a curated name to duplicate it would collide with the override rule.

## Ruled out

**Demo paths.** "Unreachable, attract-mode only" is a property of a whole class, so it belongs to the demo flag ([36](item-036-hide-demo-paths.md)) rather than to 25 copies of one sentence. The five paths that carry a demo spawn point but no entry in the decomp's demo table — `BR P7`/`P8`/`P29`, `SV P14`, `FD P8` — were weighed as a per-path fact and skipped too: that describes the game's tooling, not the place.

**A target, or a backlog entry saying "write more".** This is why the item is *retired rather than completed*. Fifteen paths carry a note, there is no number that would be the right number, and an open item asking for more invites forced ones — which is the exact failure the criteria above exist to prevent. A note arrives when a path turns out to have something odd about it, not on a schedule.

## Findings

**Nothing displayed a path note in the plumbing batch, and all three candidate surfaces were built and taken back out.** The tooltip is invisible on touch; a line under the path row goes unread on a phone, because picking a path closes the drawer; a toast expires. Where a note belongs became its own item, [39](item-039-where-am-i-surface.md), and the place panel is the answer.

**The union shape was chosen over uniform objects to protect blame.** An entry is `string | {name?, note?}`, collapsed in `sanitizeAnnotations` so callers only ever see the object, and only the paths with something extra to say expand. Rewriting all ~160 curated lines into uniform objects would have cost a `.git-blame-ignore-revs` entry to keep blame readable — and the evidence for each name lives in its commit message, so that blame is load-bearing.

## Shipped

Three commits. **The level note first** — a field that had shipped in `annotations.json` when the annotations plumbing landed and had never reached a screen, because the off-map destination tooltip showed the level's name and dropped its note. AO's `S1` pair now says what the menu level is.

Then **the path shape**, and then **thirteen notes**: the zulag 13/14 signage slip in both halves, nine secret areas built from another level's artwork, the Mines' pixel-identical escape route, and FeeCo's unnumbered terminal. Two more followed on 2026-07-30.

The research the curated names were derived from is spent as far as notes go: everything in it that justified one has landed or been ruled out, so a further batch needs fresh work rather than a second pass over the same material. AO is the obvious gap: it has no notes at all, and its curated names come from walkthroughs rather than from artwork.
