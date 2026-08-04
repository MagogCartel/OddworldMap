# 78. A tag row that filters What's New

**Status:** shipped 2026-08-02 · **Effort:** small (viewer) · **Where:** anywhere — viewer-only

Never filed as an idea before it was built, and took its number afterwards.

## What and why

The feed had grown past what anyone scrolls. Every entry already carried one of three tags — `new`, `improved`, `fixed` — and nothing surfaced them, so a reader who came to find out what had broken and been fixed read the whole journal to find out.

## Decided

**The row is built from the tags `changelog.json` actually carries, not from a list in the code.** A fourth tag therefore arrives with the entry that introduces it, and needs one word in `tests/unit/changelog.test.js`'s tag set and a colour rule — no JavaScript at all.

**That gate moved from the code into the test rather than disappearing.** With no runtime whitelist left, a typo'd tag would otherwise mint a phantom chip and a dim label with nothing anywhere to catch it, so the test's tag set is now the only thing standing between the two.

**Alphabetically, because every data order churns.** First appearance and frequency both reshuffle the row as the feed grows, and a row that reorders itself as entries land is a row nobody can learn.

**A chip and an entry's label are the same `.wn-tag wn-tag-<tag>`**, so the only styling a new tag can want is a colour rule, and without one it takes the dim default.

**Which is why the chip's fill is what says on or off.** The text colour belongs to the tag, and `fixed` is already dim, so fading it says nothing — the state had to be carried by something the tag's own palette does not already use.

**The filter is never stored, and every open clears it.** A filter left on from a past visit would hide the very updates the button's dot is announcing, which is the one thing this row must never do.

## Findings

An entry carrying no tag has no chip governing it, so it shows whatever the row says. That falls out of building the row from the data rather than from a list, and is the behaviour to keep: an untagged entry is not a fourth category to be filtered away.

## Shipped

*Give What's New a tag row that filters the feed* (`936115c`), with the operational half — a new tag wants a colour rule and one word in the test's tag set — in [CLAUDE.md](../CLAUDE.md).
