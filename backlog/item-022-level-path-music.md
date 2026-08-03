# 22. Level/path music

**Status:** deferred — recorded for the feasibility question, not queued · **Effort:** moderate for the offline render; very large in the browser · **Where:** an offline render is a tool of its own; the toggle is viewer-only

## What and why

Play the current level's music behind an opt-in sound toggle. Recorded because the feasibility question is interesting, not because it is queued.

## Findings

The discs store *sequenced* music, not streamed audio — each level's LVL holds a SEQ bank (`R1SEQ.BSQ`) played through a VAB instrument bank (`RFSNDFX.VH` / `.VB`), and the path→sequence mapping lives in the level's SoundBlockInfo. Playing it means either rendering SEQ+VAB to OGG **offline** (feasible with PSX SEQ/VAB tooling — PSF conversion, vgmstream, or the alive_reversing audio path — moderate effort) and hosting per-level clips, or a JS SPU+SEQ synth in the browser, which is very hard and not worth it.

## Ruled out

Hosting the actual soundtrack is direct distribution of copyrighted audio: even behind a toggle, the files are served from the site. Not worth it for a fan project — revisit only with explicit licensing.
