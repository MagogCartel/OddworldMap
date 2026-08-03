import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sanitizeGlossary, setGlossary, glossaryProse } from "../../public/js/glossary.js";

const load = (name) =>
  JSON.parse(readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8"));

test("sanitizeGlossary: keeps only string entries in the known sections", () => {
  const g = sanitizeGlossary({
    byField: { scale: "ok", bad: 3, empty: "" },
    byGameType: { "T::X": "ok" },
    byType: { "A.b": "ok", "C.d": null },
    junk: { x: "dropped" },
  });
  assert.deepEqual(g, {
    byField: { scale: "ok" },
    byGameType: { "T::X": "ok" },
    byType: { "A.b": "ok" },
  });
  // garbage / missing input never throws and yields empty sections
  assert.deepEqual(sanitizeGlossary(null), { byType: {}, byGameType: {}, byField: {} });
});

test("glossaryProse: resolves most-specific tier first, null on miss", () => {
  setGlossary({
    byField: { start_state: "global", scale: "plane" },
    byGameType: { "Path_Slig::StartState": "group" },
    byType: { "Mudokon.state": "specific" },
  });
  // specific wins over group and global
  assert.equal(glossaryProse("Slig", "start_state", "Path_Slig::StartState"), "group");
  assert.equal(glossaryProse("Door", "start_state", "DoorStates"), "global"); // no group/specific -> global by name
  assert.equal(glossaryProse("Mudokon", "state", "Mud_State"), "specific");
  assert.equal(glossaryProse("Slig", "scale", "Scale_short"), "plane"); // global
  assert.equal(glossaryProse("Slig", "unknown_field", undefined), null);
  setGlossary(null); // reset for other tests importing this module
});

test("glossary.json: every key names a real field / type / game type", () => {
  const g = load("glossary.json");
  const fieldNames = new Set();
  const typeFields = {}; // Type -> Set(field)
  for (const game of ["ao", "ae"]) {
    for (const lv of load(`map_data_${game}.json`).levels)
      for (const p of lv.paths)
        for (const t of p.tlvs)
          for (const k of Object.keys(t.fields || {})) {
            fieldNames.add(k);
            (typeFields[t.name] ??= new Set()).add(k);
          }
  }
  const gameTypes = new Set();
  for (const game of ["ao", "ae"])
    for (const byField of Object.values(load(`field_types_${game}.json`)))
      for (const gt of Object.values(byField)) gameTypes.add(gt);

  for (const k of Object.keys(g.byField || {}))
    assert.ok(fieldNames.has(k), `byField "${k}" is a real field name`);
  for (const k of Object.keys(g.byGameType || {}))
    assert.ok(gameTypes.has(k), `byGameType "${k}" is a real game type`);
  for (const k of Object.keys(g.byType || {})) {
    // exactly one dot: glossaryProse looks up the full "Type.field" string, so a
    // stray "Type.field.x" would validate on its first two parts yet never resolve
    const parts = k.split(".");
    assert.ok(
      parts.length === 2 && typeFields[parts[0]]?.has(parts[1]),
      `byType "${k}" is a real "Type.field"`,
    );
  }
});
