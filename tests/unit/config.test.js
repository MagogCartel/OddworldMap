import { test } from "node:test";
import assert from "node:assert/strict";
import { CATS, ENEMY_CAT, PENS, barrierDir, catOf, markerShown } from "../../public/js/config.js";

test("catOf buckets known names and falls back to meta", () => {
  assert.equal(catOf({ name: "LCDStatusBoard" }).key, "board");
  assert.equal(catOf({ name: "Slig" }).key, "enemy");
  assert.equal(catOf({ name: "HandStone" }).key, "switch");
  assert.equal(catOf({ name: "NoSuchObject" }).key, "meta");
});

test("CATS keys are unique", () => {
  const keys = CATS.map((c) => c.key);
  assert.equal(new Set(keys).size, keys.length);
});

test("markerShown: barriers ride the Enemies toggle, but only while pens are on", () => {
  const bound = { name: "SligBoundLeft" }; // meta bucket, off by default
  const slig = { name: "Slig" };
  assert.equal(catOf(bound).key, "meta");
  assert.equal(markerShown(bound), false); // the pens setting defaults off
  assert.equal(markerShown(slig), true);
  PENS.on = true;
  try {
    assert.equal(markerShown(bound), true); // pens on, enemies on, meta off
    ENEMY_CAT.on = false;
    assert.equal(markerShown(bound), false);
    assert.equal(markerShown(slig), false);
    catOf(bound).on = true; // its own bucket still shows it, pens or no pens
    assert.equal(markerShown(bound), true);
  } finally {
    PENS.on = false;
    ENEMY_CAT.on = true;
    catOf(bound).on = false;
  }
});

test("barrierDir: the side the pen lies on", () => {
  assert.equal(barrierDir({ name: "SligBoundLeft" }), 1);
  assert.equal(barrierDir({ name: "ScrabRightBound" }), -1);
  assert.equal(barrierDir({ name: "EnemyStopper", fields: { stop_direction: 0 } }), 1);
  assert.equal(barrierDir({ name: "EnemyStopper", fields: { stop_direction: 1 } }), -1);
  assert.equal(barrierDir({ name: "EnemyStopper", fields: { stop_direction: 2 } }), 0);
  assert.equal(barrierDir({ name: "MovingBombStopper" }), 0);
  assert.equal(barrierDir({ name: "Slig" }), null); // not a barrier
});

// NAME_CAT is built by forEach, so a name listed twice would silently last-win
test("no TLV name is claimed by two categories", () => {
  const seen = new Map();
  for (const c of CATS)
    for (const n of c.names) {
      assert.ok(!seen.has(n), `"${n}" is in both "${seen.get(n)}" and "${c.key}"`);
      seen.set(n, c.key);
    }
});
