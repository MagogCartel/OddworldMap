import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const load = (name) => JSON.parse(readFileSync(new URL(`../../${name}`, import.meta.url), "utf8"));
const AO = load("field_types_ao.json");
const AE = load("field_types_ae.json");

test("field types: shape is object -> { field: non-empty type string }", () => {
  for (const [game, ft] of [
    ["AO", AO],
    ["AE", AE],
  ])
    for (const [obj, fields] of Object.entries(ft)) {
      assert.ok(fields && typeof fields === "object", `${game} ${obj}`);
      for (const [f, ty] of Object.entries(fields))
        assert.ok(typeof ty === "string" && ty.length, `${game} ${obj}.${f}`);
    }
});

test("field types: a shared enum groups across objects under one key", () => {
  // Slig, SligSpawner (and AE's SligGetPants) all declare start_state as the same
  // enum, so keying by type lets one value transform serve them all
  assert.equal(AO.Slig.start_state, "Path_Slig::StartState");
  assert.equal(AO.SligSpawner.start_state, AO.Slig.start_state);
  assert.equal(AE.SligSpawner.start_state, AE.Slig.start_state);
  assert.equal(AE.SligGetPants.start_state, AE.Slig.start_state);
  assert.equal(AE.Slig.start_state, AO.Slig.start_state); // stable across games
});

test("field types: same field name on unrelated types stays a distinct key", () => {
  // start_state is a Slig AI state, a Door lock, a TrapDoor state, a MeatSaw
  // state — four unrelated enums that must never collide onto one transform
  const keys = [AO.Slig, AO.Door, AO.TrapDoor, AO.MeatSaw].map((o) => o.start_state);
  assert.equal(new Set(keys).size, 4);
  assert.equal(AO.Door.start_state, "DoorStates");
  assert.equal(AO.TrapDoor.start_state, "Path_TrapDoor::StartState");
});

test("field types: value-type fields key by their shared C type", () => {
  assert.equal(AO.Slog.asleep, "Choice_short"); // the 0/1 -> bool transform
  assert.equal(AO.Mudokon.deaf, "Choice_short");
  assert.equal(AO.Slig.scale, "Scale_short");
  assert.equal(AE.Mudokon.state, "Mud_State");
  assert.equal(AE.Mudokon.emotion, "Mud_TLV_Emotion");
});

test("field types: every entry names a real field the object carries in map_data", () => {
  for (const [game, ft, dataFile] of [
    ["AO", AO, "map_data_ao.json"],
    ["AE", AE, "map_data_ae.json"],
  ]) {
    const real = {}; // object name -> the set of field keys seen on it in map_data
    for (const L of load(dataFile).levels)
      for (const P of L.paths)
        for (const t of P.tlvs)
          if (t.fields) for (const k of Object.keys(t.fields)) (real[t.name] ??= new Set()).add(k);
    for (const [obj, fields] of Object.entries(ft)) {
      if (!real[obj]) continue; // a schema type with no instances in shipped levels
      for (const f of Object.keys(fields))
        assert.ok(real[obj].has(f), `${game}: ${obj}.${f} typed in sidecar but not a real field`);
    }
  }
});
