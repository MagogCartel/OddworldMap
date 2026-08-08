import { test } from "node:test";
import assert from "node:assert/strict";
import { census } from "../../public/js/census.js";
import { setGeometry } from "../../public/js/state.js";
import { AO_GEOMETRY, dataset, level, path, tlv } from "./fixtures.js";

// an object placed inside cell's visible window, off world units in
const obj = (name, cell, off = 50) => ({
  ...tlv(name),
  x1: cell * 1024 + 256 + off,
  y1: 120 + off,
  x2: cell * 1024 + 256 + off + 10,
  y2: 120 + off + 10,
});

// current path spans two cells; a sibling path, and a demo path in another
// level (a DemoSpawnPoint is what makes one, and the setting defaults off)
const P1 = path(1, [obj("Slig", 0), obj("Door", 0, 80), obj("Slig", 1)], [], 2, 1);
const P2 = path(2, [obj("Slig", 0)]);
const P3 = path(3, [obj("Slig", 0), obj("DemoSpawnPoint", 0, 80)]);
const L1 = level("L1", P1, P2);
const DATA = dataset([L1, level("L2", P3)], AO_GEOMETRY);

test("census: one row per name, tiers nested, demo paths tallied apart", () => {
  setGeometry(AO_GEOMETRY);
  const { rows, demo } = census(["Slig", "Door"], DATA, L1, P1, 0);
  assert.deepEqual(rows, [
    { name: "Slig", screen: 1, path: 2, level: 3, game: 3 },
    { name: "Door", screen: 1, path: 1, level: 1, game: 1 },
  ]);
  assert.equal(demo, 1); // the hidden path's Slig, out of every tier's sum
});

test("census: no cell means no screen tier", () => {
  setGeometry(AO_GEOMETRY);
  const { rows } = census(["Door"], DATA, L1, P1, null);
  assert.deepEqual(rows, [{ name: "Door", screen: null, path: 1, level: 1, game: 1 }]);
});
