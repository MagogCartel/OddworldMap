import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sanitizeTypeInfo, setTypeInfo, typeProse, typeSummary } from "../../public/js/typeinfo.js";

const load = (name) =>
  JSON.parse(readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8"));

// an entry is prose: it opens capitalized and closes punctuated
const SENTENCE = /^[A-Z].*[.!?]$/;
const SUMMARY_MAX = 160; // the first sentence rides the hover tooltip alone

test("sanitizeTypeInfo: keeps only string entries of the types section", () => {
  assert.deepEqual(sanitizeTypeInfo({ types: { A: "ok", B: 3, C: "" }, junk: { D: "x" } }), {
    A: "ok",
  });
  assert.deepEqual(sanitizeTypeInfo(null), {});
  assert.deepEqual(sanitizeTypeInfo("nonsense"), {});
  assert.deepEqual(sanitizeTypeInfo({ types: "nonsense" }), {});
});

test("typeProse / typeSummary: paragraph, first sentence, null on miss", () => {
  setTypeInfo({ types: { X: "First bit. Second bit.", Y: "One sentence only." } });
  assert.equal(typeProse("X"), "First bit. Second bit.");
  assert.equal(typeSummary("X"), "First bit.");
  assert.equal(typeSummary("Y"), "One sentence only.");
  assert.equal(typeProse("Z"), null);
  assert.equal(typeSummary("Z"), null);
  setTypeInfo(null); // reset for other tests importing this module
});

test("glossary_types.json: every key names a shipped type, prose reads as prose", () => {
  const names = new Set();
  for (const game of ["ao", "ae"])
    for (const lv of load(`map_data_${game}.json`).levels)
      for (const p of lv.paths) for (const t of p.tlvs) names.add(t.name);
  const raw = load("glossary_types.json");
  const info = sanitizeTypeInfo(raw);
  assert.ok(Object.keys(info).length > 0, "glossary_types.json holds entries");
  assert.equal(Object.keys(info).length, Object.keys(raw.types).length, "sanitize dropped none");
  setTypeInfo(raw);
  for (const [k, v] of Object.entries(info)) {
    assert.ok(names.has(k), `"${k}" is a shipped type name`);
    assert.match(v, SENTENCE, `${k}: entry reads as prose`);
    const s = typeSummary(k);
    assert.match(s, /[.!?]$/, `${k}: first sentence closes punctuated`);
    assert.ok(s.length <= SUMMARY_MAX, `${k}: summary fits a tooltip line (${s.length})`);
  }
  // exact coverage: a rebuild that surfaces a new type fails here until the
  // encyclopedia covers it
  assert.deepEqual(Object.keys(info).sort(), [...names].sort(), "one entry per shipped type");
  setTypeInfo(null);
});
