// The page's relive_api exporter against the builder's. Neither can be run from
// the other's language, so both answer to tests/fixtures/relive-digests.json: the
// builder regenerates and byte-compares it in tools/tests, and every path here
// has to hash to the same string.

import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

import {
  bucketCells,
  canonical,
  cameraId,
  exportPath,
  norm,
  widenValue,
} from "../../public/js/reliveexport.js";

const load = (f) => JSON.parse(readFileSync(new URL(`../../public/${f}`, import.meta.url), "utf8"));
const DIGESTS = JSON.parse(
  readFileSync(new URL("../fixtures/relive-digests.json", import.meta.url), "utf8"),
);
const GAMES = ["AO", "AE"];
const data = Object.fromEntries(GAMES.map((g) => [g, load(`map_data_${g.toLowerCase()}.json`)]));
const side = Object.fromEntries(
  GAMES.map((g) => [g, load(`relive_export_${g.toLowerCase()}.json`)]),
);

const paths = (g) =>
  data[g].levels.flatMap((level) => level.paths.map((path) => ({ level, path })));

test("every path exports to the digest the builder recorded", () => {
  for (const g of GAMES) {
    const want = DIGESTS[g];
    const got = {};
    for (const { level, path } of paths(g)) {
      const { doc } = exportPath(g, data[g].geometry, level, path, side[g]);
      got[`${level.short} P${path.id}`] = createHash("sha256").update(canonical(doc)).digest("hex");
    }
    assert.deepEqual(got, want, `${g} documents differ from the builder's`);
  }
});

// the two rules part only over a rect that straddles a cell boundary, so this is
// what a regression to the other game's rule would misplace — the same count the
// builder's own suite pins
test("each game's cell rule is the one in force", () => {
  const straddling = { AO: 3, AE: 835 };
  for (const g of GAMES) {
    const geo = data[g].geometry;
    const corner = (t, p) => Math.floor(t.y1 / geo.worldH) * p.w + Math.floor(t.x1 / geo.worldW);
    const midpoint = (t, p) =>
      Math.floor(Math.floor((t.y1 + t.y2) / 2) / geo.worldH) * p.w +
      Math.floor(Math.floor((t.x1 + t.x2) / 2) / geo.worldW);
    const [mine, other] = g === "AO" ? [corner, midpoint] : [midpoint, corner];
    let moved = 0;
    for (const { path } of paths(g))
      for (const [cell, tlvs] of bucketCells(g, path, geo))
        for (const t of tlvs) {
          assert.equal(mine(t, path), cell, g);
          if (other(t, path) !== cell) moved++;
        }
    assert.equal(moved, straddling[g], g);
  }
});

test("a written document carries every property relive reads", () => {
  for (const g of GAMES) {
    const registered = {};
    for (const s of Object.values(side[g].schema.structures))
      registered[s.name] = s.properties.map((p) => p.name);
    for (const { level, path } of paths(g)) {
      const { doc, manifest } = exportPath(g, data[g].geometry, level, path, side[g]);
      assert.deepEqual([...manifest.missing], [], `${g} ${level.short} P${path.id}`);
      for (const cam of doc.map.cameras)
        for (const o of cam.map_objects) {
          const keys = new Set(Object.keys(o.properties));
          for (const n of [
            "xpos",
            "ypos",
            "width",
            "height",
            ...registered[o.object_structures_type],
          ])
            assert.ok(keys.has(n), `${g} ${o.object_structures_type} is missing ${n}`);
        }
    }
  }
});

// the surviving fallback is what a diff against a reference export holds
// known-divergent, so a new one must not appear silently
test("only the pinned fallbacks stand in for an unarchived word", () => {
  const want = { AO: [], AE: ["MovieHandstone.Trigger Switch ID"] };
  for (const g of GAMES) {
    const used = new Set();
    for (const { level, path } of paths(g)) {
      const { manifest } = exportPath(g, data[g].geometry, level, path, side[g]);
      for (const f of manifest.fallbacks) used.add(f);
    }
    assert.deepEqual([...used].sort(), want[g], g);
  }
});

test("the camera set is the named cameras plus the cells holding objects", () => {
  for (const g of GAMES) {
    for (const { level, path } of paths(g)) {
      const { doc } = exportPath(g, data[g].geometry, level, path, side[g]);
      const cells = new Set(doc.map.cameras.map((c) => c.y * path.w + c.x));
      for (const c of path.cams) assert.ok(cells.has(c.cell), `${g} ${level.short} camera cell`);
      assert.equal(
        doc.map.cameras.reduce((n, c) => n + c.map_objects.length, 0),
        path.tlvs.length,
        `${g} ${level.short} P${path.id} object count`,
      );
      for (const c of doc.map.cameras) {
        assert.ok(c.x >= 0 && c.x < path.w && c.y >= 0 && c.y < path.h);
        assert.equal(c.id, c.name ? cameraId(c.name) : 0);
      }
    }
  }
});

test("a collision item carries its link words, not the editor's default", () => {
  for (const g of GAMES) {
    const linkNames = side[g].schema.collision_structure.slice(5).map((r) => r.name);
    const at = linkNames.map((n) => side[g].links.columns.indexOf(norm(n)));
    assert.ok(!at.includes(-1), `${g} links.columns misses a link word`);
    let carried = 0;
    for (const { level, path } of paths(g)) {
      const { doc } = exportPath(g, data[g].geometry, level, path, side[g]);
      const rows = side[g].links.paths[level.short][String(path.id)];
      assert.equal(doc.map.collisions.items.length, path.lines.length);
      doc.map.collisions.items.forEach((item, i) => {
        linkNames.forEach((n, j) => {
          assert.equal(item[n], rows[i][at[j]]);
          if (item[n] !== -1) carried++;
        });
      });
    }
    assert.ok(carried > 0, `${g} writes every link as -1`);
  }
});

test("widenValue reads a stored word at the property's own width", () => {
  assert.equal(widenValue(-1, undefined, "SInt16", 2), -1);
  assert.equal(widenValue(-1, undefined, "UInt16", 2), 0xffff);
  assert.equal(widenValue(0x1ff, undefined, "Byte", 1), 0xff);
  // a missing high word sign-extends, so a lone negative stays negative
  assert.equal(widenValue(-2, undefined, "SInt32", 4), -2);
  assert.equal(widenValue(0, 1, "SInt32", 4), 0x10000);
  assert.equal(widenValue(0, -1, "SInt32", 4), -65536);
  assert.equal(widenValue(0, -1, "Uint32", 4), 0xffff0000);
});

test("norm reduces a display string the way the builder's does", () => {
  assert.equal(norm("Next 2"), "next_2");
  assert.equal(norm("ID (Unused?)"), "id");
  assert.equal(norm("Abe's Start"), "abes_start");
});
