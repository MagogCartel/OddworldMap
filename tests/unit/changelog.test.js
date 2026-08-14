import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// Schema sanity over the shipped changelog: the invariants the What's New
// panel relies on. changelog.json is hand-curated, so this guards against
// a typo shipping a broken feed.

const load = (name) =>
  JSON.parse(readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8"));

const TAGS = new Set(["new", "improved", "fixed"]);
const KEYS = new Set(["date", "tag", "title", "detail", "flagship"]);

test("changelog.json matches the What's New panel's expectations", () => {
  const data = load("changelog.json");
  assert.ok(Array.isArray(data.entries) && data.entries.length > 0, "entries is a non-empty array");

  let prev = null;
  for (const [i, e] of data.entries.entries()) {
    assert.ok(typeof e.title === "string" && e.title.length > 0, `entry ${i} has a title`);
    assert.match(e.date, /^\d{4}-\d{2}-\d{2}$/, `entry ${i} date is YYYY-MM-DD`);
    // a misspelt key is read by nobody and reported by nothing else
    for (const k of Object.keys(e)) assert.ok(KEYS.has(k), `entry ${i} key ${k} is known`);
    if ("detail" in e) assert.equal(typeof e.detail, "string", `entry ${i} detail is a string`);
    if ("tag" in e) assert.ok(TAGS.has(e.tag), `entry ${i} tag is one of new/improved/fixed`);
    // the mark exists to be true, and reads as "new · flagship" in the panel
    if ("flagship" in e) assert.equal(e.flagship, true, `entry ${i} flagship is true`);
    if (e.flagship) assert.equal(e.tag, "new", `entry ${i} is flagship, so its kind is new`);
    if (prev) assert.ok(e.date <= prev, `entry ${i} is newest-first (dates non-increasing)`);
    prev = e.date;
  }
  assert.ok(
    data.entries.some((e) => e.flagship),
    "the feed carries a flagship, so the row has its chip",
  );
});
