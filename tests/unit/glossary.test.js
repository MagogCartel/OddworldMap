import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  sanitizeGlossary,
  setGlossary,
  glossaryProse,
  fieldUnit,
} from "../../public/js/glossary.js";
import { UNITS } from "../../public/js/fields.js";

const load = (name) =>
  JSON.parse(readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8"));

test("sanitizeGlossary: keeps only string entries in the known sections", () => {
  const g = sanitizeGlossary({
    byField: { scale: "ok", bad: 3, empty: "" },
    byGameType: { "T::X": "ok" },
    byType: { "A.b": "ok", "C.d": null },
    junk: { x: "dropped" },
    units: { byField: { delay: "frames", bad: 3 }, byType: { "A.b": "grid" }, junk: 1 },
  });
  assert.deepEqual(g, {
    byField: { scale: "ok" },
    byGameType: { "T::X": "ok" },
    byType: { "A.b": "ok" },
    units: { byField: { delay: "frames" }, byGameType: {}, byType: { "A.b": "grid" } },
  });
  // garbage / missing input never throws and yields empty sections
  const bare = { byType: {}, byGameType: {}, byField: {} };
  assert.deepEqual(sanitizeGlossary(null), { ...bare, units: bare });
  assert.deepEqual(sanitizeGlossary({ units: "nonsense" }), { ...bare, units: bare });
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

test("fieldUnit: the same three tiers over the units section, null on a miss", () => {
  setGlossary({
    byField: { delay: "A delay." },
    units: {
      byField: { delay: "frames", reach: "grid" },
      byGameType: { "Path_Slig::Delay": "seconds" },
      byType: { "Slig.delay": "percent" },
    },
  });
  assert.equal(fieldUnit("Slig", "delay", "Path_Slig::Delay"), "percent"); // specific wins
  assert.equal(fieldUnit("Scrab", "delay", "Path_Slig::Delay"), "seconds"); // group next
  assert.equal(fieldUnit("Scrab", "delay", undefined), "frames"); // global by name
  assert.equal(fieldUnit("Scrab", "reach", undefined), "grid");
  assert.equal(fieldUnit("Scrab", "untouched", undefined), null);
  // prose and unit are independent: a defined field need carry no unit
  setGlossary({ byField: { delay: "A delay." } });
  assert.equal(fieldUnit("Scrab", "delay", undefined), null);
  setGlossary(null);
});

test("glossary_fields.json: every key names a real field / type / game type", () => {
  const g = load("glossary_fields.json");
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

  // the units section repeats the three tiers, so it is held to the same keys
  for (const [label, tiers] of [
    ["", g],
    ["units.", g.units || {}],
  ]) {
    for (const k of Object.keys(tiers.byField || {}))
      assert.ok(fieldNames.has(k), `${label}byField "${k}" is a real field name`);
    for (const k of Object.keys(tiers.byGameType || {}))
      assert.ok(gameTypes.has(k), `${label}byGameType "${k}" is a real game type`);
    for (const k of Object.keys(tiers.byType || {})) {
      // exactly one dot: the tier walk looks up the full "Type.field" string, so a
      // stray "Type.field.x" would validate on its first two parts yet never resolve
      const parts = k.split(".");
      assert.ok(
        parts.length === 2 && typeFields[parts[0]]?.has(parts[1]),
        `${label}byType "${k}" is a real "Type.field"`,
      );
    }
  }

  // a def is prose among labels: it opens capitalized and closes punctuated,
  // and never enumerates values — fieldHelp appends the value list itself
  for (const section of ["byType", "byGameType", "byField"])
    for (const [k, v] of Object.entries(g[section] || {})) {
      assert.match(v, /^[A-Z].*[.!?]$/, `${section} "${k}" reads as prose`);
      assert.ok(!/\b0 = |\b1 = /.test(v), `${section} "${k}" leaves the value list to fieldHelp`);
    }
});

// a unit outside the closed set finds no formatter and renders as the bare int,
// which is a typo shipping as if nothing were wrong
test("glossary_fields.json: every unit is one the renderer formats", () => {
  const units = load("glossary_fields.json").units || {};
  for (const section of ["byType", "byGameType", "byField"])
    for (const [k, v] of Object.entries(units[section] || {}))
      assert.ok(UNITS[v], `units.${section} "${k}" names a unit UNITS formats, not "${v}"`);
});

// full coverage: a rebuild that surfaces a new field fails here until the
// glossary covers it
test("every shipped field resolves a definition", () => {
  setGlossary(load("glossary_fields.json"));
  const fieldTypes = {
    ao: load("field_types_ao.json"),
    ae: load("field_types_ae.json"),
  };
  const missing = new Set();
  for (const game of ["ao", "ae"])
    for (const lv of load(`map_data_${game}.json`).levels)
      for (const p of lv.paths)
        for (const t of p.tlvs)
          for (const k of Object.keys(t.fields || {}))
            if (!glossaryProse(t.name, k, fieldTypes[game][t.name]?.[k]))
              missing.add(`${t.name}.${k}`);
  setGlossary(null);
  assert.deepEqual([...missing].sort(), [], "every field has a def");
});
