# 89. What the packed layout still misreports

**Status:** open · **Effort:** small each (viewer) · **Where:** anywhere, no disc · **Filed:** 2026-08-14, out of the camera-window work

## What it is

Both games address cameras on a grid coarser than the screen, and the map lays the screens edge to edge, folding the slack between windows out of existence. Objects authored in that slack now say so: a marker draws solid where it covers screen and dotted where it does not. Two surfaces still speak as though the slack were not there.

**Collision lines.** 2385 of AO's 5790 line endpoints sit in the slack, and 665 of AE's 13290. A floor line drawn across a gap is one continuous stroke that silently skips 656 world units, and the ruler measuring along it reports the packed distance rather than the real one. `worldLen` says so in [js/state.js](../public/js/state.js), and that is the whole of the disclosure.

**Per-screen counts.** The screen list and the numbers panel bucket a marker by its drawn centre, so one folded onto a neighbour is counted there: 1051 of AO's 5623 markers are tallied under a screen they cover no part of, against 2 of AE's 10602. The row carries an `offscreen` tag where nothing of it is on screen at all, but the header count and the By-the-numbers screen tier still count it where it landed.

## Decided: the packing itself stays

The slack is not level the player ever occupies. A camera change teleports the character across it with the within-cell offset preserved (`VOnPathTransition_401470` in AO, `vOnPathTransition_408320` in AE), so nothing walks it and the games render none of it. Folding it away is a truthful compaction, not a lie, and the map is far more readable for it.

**Ruled out: laying the screens out at their true world pitch as the default.** Measured 2026-08-14 over the shipped data: AO's largest path, `C1 P1`, goes from 3680x2400 draw units to 10240x4800, 5.6x the area, nearly all of it empty. AE barely moves, 1.1x, its slack being 7x20 against AO's 656x240. A default that makes Oddysee five times emptier to browse buys back space no one can stand in.

It survives as a Display toggle if anyone wants it, and it is cheaper to build now than it was: permalinks carry world coordinates, so a route or a view plotted in one spacing means the same place in the other. Before that it would have moved every shared link.

## Sketch

The two halves want different answers and should not be bundled into one change.

- **Lines**: the marker treatment ported over, a stroke that dots across the folded gap. The complication markers do not have is that a line is not a rect, so the split is per-segment rather than a clip, and `screenRuns` in [js/model.js](../public/js/model.js) answers about spans rather than points. Whether the ruler should then report the true distance is a separate question with a worse answer than it looks: the honest number counts ground nobody can cross.
- **Counts**: bucket by coverage rather than by drawn centre, so a marker is counted under each screen it actually covers, or under none. That is a change to `inCell` in [js/census.js](../public/js/census.js) and the matching rule in [js/campanel.js](../public/js/campanel.js), which CLAUDE.md requires to agree. It also makes a straddling marker countable twice, which is either right or a new lie depending on what the count is for.

## Watch out

The counting rule is load-bearing for two surfaces that are pinned against each other, and the screen list is the touch device's only inspection surface. Changing what a screen holds changes what a phone user is shown, so the tag and the count should end up saying the same thing rather than a third one.
