import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../../public/index.html", import.meta.url), "utf8");

// opening tags with their attributes, each tag spanning as many lines as Prettier wrapped it over
const TAGS = [...html.matchAll(/<([a-z]+)\b([^>]*)>/gs)].map(([, name, attrs]) => ({
  name,
  cls: attrs.match(/\bclass="([^"]*)"/)?.[1] ?? "",
  id: attrs.match(/\bid="([^"]*)"/)?.[1],
  title: attrs.match(/\btitle="([^"]*)"/)?.[1],
  tip: attrs.match(/\bdata-tip="([^"]*)"/)?.[1],
}));
const named = (t) => t.id ?? `<${t.name} class="${t.cls}">`;

// the attribute carries the entity rather than a newline, and each line is a sentence
const wellFormed = (tip) =>
  tip.split("&#10;").every((l) => /^[A-Z]/.test(l.trim()) && /[.!?]$/.test(l.trim()));

test("markup: an action button's tooltip is a data-tip, never a title", () => {
  const buttons = TAGS.filter((t) => t.cls.split(/\s+/).includes("actbtn"));
  assert.ok(buttons.length >= 7, `swept ${buttons.length} action buttons`);
  for (const b of buttons) assert.equal(b.title, undefined, `${named(b)} carries a native title`);
  for (const id of ["graphBtn", "exportBtn", "exportPathBtn", "numbersBtn", "editBtn"]) {
    const el = TAGS.find((t) => t.id === id);
    assert.ok(el, `${id} is in the markup`);
    assert.ok(el.tip, `${id} carries a data-tip`);
  }
});

test("markup: no element offers two tooltips at once", () => {
  for (const t of TAGS) assert.ok(!(t.tip && t.title), `${named(t)} carries both`);
});

test("markup: every data-tip reads as sentences", () => {
  const tips = TAGS.filter((t) => t.tip);
  assert.ok(tips.length >= 17, `swept ${tips.length} tips`);
  for (const t of tips) assert.ok(wellFormed(t.tip), `${named(t)}: ${t.tip}`);
  // every shipped string passes, so the predicate answers for itself on two that must not
  assert.ok(!wellFormed("draws the thing."), "a lowercase opening is not a sentence");
  assert.ok(!wellFormed("Draws the thing"), "an unpunctuated line is not a sentence");
  assert.ok(wellFormed("Draws the thing.&#10;And the detail behind it."));
});
