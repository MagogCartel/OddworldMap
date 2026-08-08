# 87. By the numbers — an object-count explorer

**Status:** shipped 2026-08-08 · **Effort:** medium (viewer) · **Where:** anywhere · **Filed:** 2026-08-07 feature-ideation sweep

## Why

The map can find every instance of a thing (search) and list one screen's things (the screen list), but it cannot *count*: how many Mudokons this path holds, how many mines this level, how the Brewery's drills spread across its zulags. The sidebar's per-category counts answer only the current path, only per category. Counting is the trivia engine ("zulag 3 holds more drills than anywhere else" — the claim behind an adopted nickname, checkable today only in a test file) and the completionist's ledger, and every number is derived live from loaded data, so nothing can go stale.

## The vision

Not a static trivia card. Pick the object type or types you care about, then read their counts at every granularity at once — this screen / this path / this level / this game — from a panel that keeps updating as you click around the map, the way the screen list follows the selection. First build that core; the comparisons grow on top later: path and level sizes, "this path holds 25 of the game's 181 drills, the most anywhere", how a count ranks against every other path's.

## To decide before building (the planning pass)

- **Surface**: a docked panel like the screen list (bottom sheet on phones, [4](item-004-per-camera-object-list.md) is the pattern), a fifth `.overlay` dialog, or a sidebar section. Live-follow favours the panel; dialogs cover the map they describe.
- **Selection model**: one type, a multi-type set, or whole categories too — and where the picking UI lives (the Fields picker's per-type rows are the near pattern).
- **Granularity rows**: always show all four tiers, or let the user pick; what "screen" means while zoomed out (the camera under the view centre, or none).
- **Counting rules**: how demo paths (respect the setting? say what's excluded?), the object-category filters, and background-plane objects figure into a count — a number must say what it covers.
- **Scope**: the counting core alone, or the comparisons (ranks, sizes, superlatives) with it — a rank column is ink a number has to earn.

## Watch out

- Counts state what the raw objects say and nothing more: a Mudokon count is TLVs named Mudokon, not "rescuable Mudokons" — [71](item-071-mudokon-rescue-census.md) closed on exactly that distinction and stays closed.

## Decided

A floating panel on the screen list's pattern — live-follow is the point, and it is the one surface that survives it on phones; a multi-type picker capped at six; all four tiers as fixed columns, the screen tier reading the view center and showing an em-dash when the center sits over empty margin. Counting ignores the category display filters (search's rule: filters affect display, not the data) and follows the demo-paths setting, tallying what hidden paths hold as a footnote. The counting core alone ships; the comparisons stay out.

## Shipped

_Count anything, everywhere, at a glance_: `js/census.js` (the DOM-free counting core, unit-tested; screens bucket by draw-space center so the panel and the screen list agree) and `js/numbers.js` (the panel, bottom-right where the screen list keeps bottom-left, so a desktop holds both; on narrow both are bottom sheets, so a `float-opened` event lets whichever opens close the other). The screen tier follows a new `view-changed` event dispatched from `scheduleHash`'s debounced timer — the one funnel every pan, zoom and selection settles through — rather than any pointer event. A row's name doubles as its remove button.

The comparisons the vision sketched — ranks, sizes, "the most of anywhere" — stayed out, and no item carries them: the panel answers the counting questions people actually bring, the one superlative that mattered (the nickname evidence) is already pinned by the annotations tests, and a rank column is permanent ink for a question nobody has asked. Should demand ever show up, it keys off the same census walk, and the demo footnote already models how a qualified number should read.
