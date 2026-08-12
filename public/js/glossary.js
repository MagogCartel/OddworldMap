// Curated plain-English field meanings from glossary_fields.json, resolved in three
// tiers so a field is defined once at the broadest level that fits:
//   byType["Type.field"]   — one object type's own meaning (wins)
//   byGameType["GameType"] — every object whose field has that game type (the
//                            group; Slig/SligSpawner/SligGetPants share one)
//   byField["field"]       — same meaning wherever the name appears (globals)
// The caller supplies the field's game type (from field_types), so this module
// needs no other. Leaf module: no imports, importable in bare Node.

let gloss = { byType: {}, byGameType: {}, byField: {} };

// keep only string->string entries in each known section; anything else is
// dropped, so a missing, garbage or future-shaped file can never break the viewer
export function sanitizeGlossary(raw) {
  const out = { byType: {}, byGameType: {}, byField: {} };
  if (!raw || typeof raw !== "object") return out;
  for (const section of ["byType", "byGameType", "byField"]) {
    const src = raw[section];
    if (!src || typeof src !== "object") continue;
    for (const [k, v] of Object.entries(src)) if (typeof v === "string" && v) out[section][k] = v;
  }
  return out;
}

export function setGlossary(raw) {
  gloss = sanitizeGlossary(raw);
}

// the meaning for a field, most-specific tier first, or null
export function glossaryProse(type, field, gameType) {
  return (
    gloss.byType[`${type}.${field}`] ??
    (gameType ? gloss.byGameType[gameType] : undefined) ??
    gloss.byField[field] ??
    null
  );
}
