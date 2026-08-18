# 68. Say what the repo is licensed as

**Status:** undecided — a real decision, not a task · **Effort:** tiny to write, which is not the hard part · **Where:** anywhere · **Filed:** 2026-07-24/25 review

## What it is

Three kinds of content sit in this repository under three different claims, and the repository's own metadata does not state the apportionment:

- **Code written for this project** — the viewer, `build_map.py`, the parsers, `ogcard.swift`. No stated licence.
- **One vendored file under another author's copyright** — `tools/PSXMDECDecoder.{cpp,h}`, GPL-2.0, originally from libbs / psxdev; the attribution is in the file header, where the README points rather than reproducing it.
- **Extracted game artwork** under `cams/**`, plus the object data. The project states plainly, in the README and in the About dialog, that this remains the property of its copyright holders — so this is the one tree it is not the project's to license, and it does not try to.

What ships alongside that: a root `LICENSE` carrying the verbatim GPL-2.0 text, whose only copyright lines are the FSF's own and the licence template's unfilled `<name of author>` placeholders, and no `license` field in `package.json`. The README says what the vendored decoder is licensed as and then that the rest was written for this project — which says who wrote it, not what anyone may do with it.

**The gap is between the app and the repository, and the app is the clearer of the two.** The About dialog and the README already say what this is: an unofficial fan project, unaffiliated, shipping no game code, with the extracted imagery belonging to its holders. A licence file at the root with no holder line does not restate any of that, and a hosting platform reading it will infer a repository-level licence from its presence — an inference drawn from file layout, not a claim the project has made anywhere in its own words. Closing that gap is the point of this item.

## The decision to make

Not "add a licence" but which shape is honest:

- a per-tree statement in the README — the code under a named licence, the vendored file under its own, the extracted data under neither;
- a `LICENSES/` split;
- or leaving it as it is, on the grounds that the data half cannot be licensed anyway, so any statement invites over-reading.

Whichever wins, establish what the root `LICENSE` was originally intended to cover before codifying it. The vendored decoder is GPL-2.0 and the repository is GPL-2.0, and the relationship between those two facts should be confirmed rather than assumed.

## Why it surfaced

The About dialog links the repo from inside the app, so a reader who wonders about terms lands there in one click. The dialog deliberately states **no** terms: across three claims, one line in the app would claim all three, and a bare "GPL-2.0" beside the trademark notice would read as licensing artwork this project does not own. That silence is recorded in [CLAUDE.md](../CLAUDE.md) as a decision, so it needs revisiting only when this item lands, not before. [76](item-076-site-attribution.md) records the same decision from the app's side.
