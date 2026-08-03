# 27. Search in the user's value representation

**Status:** shipped 2026-07-24 · **Effort:** small · **Where:** anywhere, viewer-only

## What and why

The "Show raw field values" setting made tooltips, the screen list and search *result rows* render raw ints, but the search *index* and the matched-field append stayed prettified. Two consequences when raw was on:

- You could not find by the raw value — `start_state=1` did not match, because the index held `start_state=patrol`.
- Searching a prettified term matched, but the row rendered raw and then re-appended the prettified matched field, so it read `start_state=1 … start_state=patrol` — duplicated, with the query highlight landing only on the appended copy.

## Sketch

Thread the raw setting into the index and the append so search operates in one representation: raw when the setting is on, prettified when off. Then matching, display and highlight agree and the duplication disappears. `getSettings().showRawValues` is global, and `tlvSearchText` has no game context, so read it directly.

Deferred deliberately at filing — the partial state was acceptable meanwhile, and it beat forcing prettified display on someone who had chosen raw.

## Findings

**There was no cache to invalidate**, which is the only reason this stayed small. The index was recomputed live, and the existing `settings-changed` listener already re-ran the search on `rawValues`, so threading the flag through was the whole change.

## Shipped

The raw flag threads into the index and the append, read once per run, so matching, display and highlight all use the one representation the user chose. Raw off is unchanged.
