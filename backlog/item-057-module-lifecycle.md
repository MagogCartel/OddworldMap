# 57. One module lifecycle: explicit `init()` everywhere

**Status:** open · **Effort:** medium (viewer refactor) · **Where:** anywhere, viewer-only · **Filed:** 2026-07-24/25 review

## The question asked: which convention is best?

Explicit `init()` for every module that touches the DOM, reads settings or registers listeners; leaf modules stay side-effect-free as they already are. Reasons, in the order that they matter here:

1. **The repo already asserts half of this rule and can then assert all of it.** [tests/unit/imports.test.js](../tests/unit/imports.test.js) enforces "no DOM at import time" for the leaf modules, and CLAUDE.md calls that guard the regression guard for the whole suite. Today the rule is "leaf modules are pure, UI modules are not", which is a rule with an exception list. After the change it is one rule — *import defines, `init` acts* — and the test can be widened to cover every module.
2. **The current boot order is a load-bearing accident.** `import "./sidebar.js"` in [js/main.js](../public/js/main.js) is hoisted, so `sidebar.js` runs `getViewSnapshot()` → `getSettings()` **before** `initSettings()` executes. It works only because `getSettings()` is lazily memoised. Nothing states that dependency; nothing tests it; any future module that reads settings eagerly at import breaks in a way lint and the DOM-free tests cannot see.
3. **Ordering becomes reviewable.** `main.js` already carries two ordering comments in prose — "before the path buttons build their labels", "before any tooltip/search prettifies". Those constraints deserve to be a call list, not comments attached to imports whose execution order is invisible.
4. **It is the precondition for [69](item-069-browser-smoke-tests.md).** A browser test wants to build a document and then call `initX()`. Modules that fire on import can only be tested by importing them into an already-correct document, which is most of why it looks expensive today.

The alternative — everything self-wires at import — is internally consistent but loses (2), (3) and (4), and would mean deleting a test that has already earned its keep.

## Current state, for the person doing this

Explicit `init`: `settings`, `fieldpanel`. Self-wiring at import: `sidebar`, `search`, `whatsnew`, `campanel`, `route`, `interaction`, `render`. Pure leaves, no change needed: `config`, `util`, `state`, `model`, `fields`, `searchquery`, `annotations`, `dialog`, `icons`.

## The one sanctioned exception: `js/dom.js`

It resolves every static element with `getElementById` at import time. That is safe because the module script is at the end of `<body>`, and making it lazy would churn every call site for no benefit. Keep it, and document it in CLAUDE.md as *the* import-time DOM access — one named exception is a convention; an unstated exception list is the current problem.

## Sketch

One module per commit, each mechanical: wrap each self-wiring module's top-level statements in an exported `initX()`, call them from `main.js` in an explicit commented order, and widen `imports.test.js` to cover every module and assert each exports its `init`.

Recommended boot order, encoding the constraints already written in the prose comments: `initSettings()` → `setAnnotations` / `setFieldTypes` / `setEnumLabels` → `initRender()` → `initSidebar()` → `initInteraction()` → `initSearch()` → `initFieldPanel()` → `initCamPanel()` → `initRoute()` → `initWhatsNew()` → `initGames(...)` → `applyHash()`.

## Watch out

**Module-level `const` DOM references** in `campanel.js`, `route.js` and `fieldpanel.js` can stay as they are — they go through `dom.js`, the sanctioned exception. Only the listener registration and DOM mutation needs to move into `init`. Moving the consts too is churn for nothing.

**`sidebar.js` does real work at import**: it reads the snapshot, mutates `CATS[].on`, builds the filter checkboxes and seeds `state.show` from the HTML `checked` attributes. All of that must move wholesale into `initSidebar()`, and `state.show` must be populated before the first `draw()`.

**`render.js`'s `COLOR` block** reads CSS custom properties at import. That is a `getComputedStyle` call, not a DOM mutation; it can stay at import or move into `initRender()`. Moving it is slightly more honest; either is defensible — pick one and be consistent with the `dom.js` decision.

**`whatsnew.js` calls `init()` at import already**, and it is `async`. Export it instead of self-calling; `main.js` should not await it, since the panel appearing late is fine and already how it behaves.

## Verify

`npm test` with the widened import test, `npm run lint`, then a full click-through: every setting, every toggle, search, cam panel, field panel, route, ruler, What's New, embed mode, and a cold load with a permalink. This is the item where a browser smoke test would pay for itself — if [69](item-069-browser-smoke-tests.md) gets un-deferred, doing it *before* this is the better order.

## Ships with

A CLAUDE.md edit — it says "`js/main.js` is the boot entry", which extends to stating the convention and the `dom.js` exception. No changelog entry.
