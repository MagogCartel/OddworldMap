# 62. Sweep the codebase for diff-justification comments

**Status:** shipped 2026-08-06 · **Effort:** small (cleanup) · **Where:** anywhere · **Filed:** 2026-07-24/25 review

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

## Shipped

Every comment in `public/js/` and `public/sw.js`, `tools/build_map.py` and `tools/changelog.py` was read in context, full-line and trailing alike. Nine came out, across five files: three in `settings.js`, three in `interaction.js`, one each in `fields.js`, `navigate.js` and `render.js`.

**The tell this item was filed for is not what the tree holds.** Nothing in `js/` or `tools/` narrates a move: no "extracted from", no "was previously", and the one past-tense line in the viewer (`model.js`'s stones viewing cameras the shipped path "no longer has") states a fact about the data, not about the code's history. The "without this, X would happen" shape does appear nine times, but each one annotates a line whose constraint is genuinely its own — a browser behaviour, a cache that would grow for the session, a hit that would read as missing — and none of them sits among bare peers doing equally non-obvious things.

**What the tree holds instead is restatement**, and that is what the nine were: a comment naming the operation the next line performs. `// persist the live settings object after a mutation` over `persistSettings`, `// the default-visible field set for a type` over `defaultVisible`, `// highlight the button whose data-key matches` over a one-line `classList.toggle`, `// anchor at pinch midpoint` on the midpoint arithmetic itself. Two were the peer-asymmetry tell in a second form: `viewChanged` and `rememberLocation` were the only members of `settings.js`'s persistence run wearing a "called by sidebar.js" / "called by navigate.js" tag, while `getViewSnapshot`, `sanitizeLocationHash` and `clearStoredLocation` beside them say what they answer with — a tag that rots the moment a second caller appears and that the import graph already answers.

**Three classes were left deliberately.** The uniform block labels inside long functions (`draw()`'s six, the builder's parse stages) restate their blocks but work as a table of contents, and cutting a consistent set costs navigation to buy nothing. A consumer named as part of a fact stays — `main.js`'s `setAnnotations(annotations); // before the path buttons build their labels` is an ordering constraint, not a cross-reference. And `tests/` is out of scope on purpose: its past-tense comments ("a link whose partner is absent used to badge paths the game never arrives at") are the specification of what a whole-set pin catches, the same idiom CLAUDE.md uses, and rewriting them present-tense would change prose without changing information.

**`model.js` and `build_map.py` came out untouched**, which is the result worth recording: the two files carrying the most comment lines in the repo at the time are the two whose comments are almost entirely format law, and the convention was already being followed where it matters most.
