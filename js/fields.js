// What object fields to show, and how to render them.
//
// The builder ships every field of a gameplay object raw in `t.fields`; this
// module owns which ones show and maps enum ints to text. The one indirection —
// visibleFields() — is what "default", "show more", and the picker all resolve
// through, so callers never change.
//
// Leaf module: no DOM/state imports, importable in bare Node for tests.

import { glossaryProse } from "./glossary.js";

// shown by default for any type that carries them: the few signals that dozens
// of unrelated types across every group share. A field only one type or one
// creature family carries belongs in DEFAULT_BY_TYPE instead.
export const GLOBAL_DEFAULT = new Set([
  "start_state", // AI state / door lock / hazard on-off — resolved per owning type
  "switch_id", // the switch a door/hazard/etc. is wired to
  "action",
]);

// per-type notable fields on top of the globals: the state/identity/direction/
// count that describes how the object behaves. Keyed by type name; a field the
// game's copy of the type doesn't carry is simply skipped, so AO-only and
// AE-only fields coexist here (a Mudokon has job in AO, state in AE).
export const DEFAULT_BY_TYPE = {
  // creatures / enemies
  BeeSwarmHole: ["movement_type"],
  CrawlingSlig: ["respawn_on_death", "state"],
  Fleech: ["asleep", "hanging"],
  Glukkon: ["glukkon_type"],
  Mudokon: ["angry_switch_id", "blind", "deaf", "emotion", "job", "rescue_switch_id", "state"],
  Paramite: ["enter_from_web", "entrance_type"],
  Scrab: ["patrol_type"],
  Slig: ["chase_abe_when_spotted", "shoot_on_sight_delay"],
  SligGetPants: ["chase_abe_when_spotted", "shoot_on_sight_delay"],
  SligSpawner: ["chase_abe_when_spotted", "shoot_on_sight_delay"],
  Slog: ["anger_switch_id", "asleep"],
  // doors & travel
  BirdPortal: ["portal_type"],
  Door: ["door_type"],
  LevelLoader: ["destination_level"],
  SlamDoor: ["start_shut"],
  TrapDoor: ["self_closing"],
  // hazards
  GasEmitter: ["colour"],
  MeatSaw: ["speed", "type"],
  RollingBall: ["roll_direction"],
  RollingBallStopper: ["direction"],
  // switches
  FootSwitch: ["triggered_by"],
  InvisibleSwitch: ["set_off_alarm"],
  // lifts & mechanisms
  Hoist: ["hoist_type"],
  LiftMover: ["move_direction"],
  LiftPoint: ["lift_point_stop_type"],
  ZBall: ["start_position"],
  // info & tomb
  LCDStatusBoard: ["number_of_mudokons", "zulag_number"],
  SlapLock: ["give_invisibility_power_up"],
  // sacks
  BoneBag: ["bone_amount"],
  MeatSack: ["amount_of_meat"],
  RockSack: ["rock_amount"],
};

// the default-visible field set for a type
export function defaultVisible(typeName) {
  const scoped = DEFAULT_BY_TYPE[typeName];
  return scoped ? new Set([...GLOBAL_DEFAULT, ...scoped]) : GLOBAL_DEFAULT;
}

// fields whose 0 means "absent" (no switch wired, flag not set) — hide it. But
// never hide a meaningful 0: shoot_on_sight_delay=0 (shoots on sight) and
// asleep=0 (awake) are real state.
export const HIDE_WHEN_ZERO = new Set([
  "switch_id",
  "rescue_switch_id",
  "angry_switch_id",
  "anger_switch_id",
  "slig_spawner_switch_id",
  "deaf",
  "blind",
]);

// value-type transforms the viewer owns (semantic, not decomp labels), keyed by
// the field's game type; a hand entry here wins over the generated enum labels.
const CHOICE = { 0: false, 1: true };
const SCALE = { 0: "full", 1: "half" };
export const TRANSFORM = {
  Choice_short: CHOICE,
  Choice_int: CHOICE,
  Scale_short: SCALE,
  Scale_int: SCALE,
};

// object -> field -> game type, and the generated enum labels (type -> value ->
// text), both per game; the boot loads the sidecars and hands them over. Empty
// until then, so prettify degrades to raw (bare tests).
let FIELD_TYPES = {};
let ENUM_LABELS = {};
export function setFieldTypes(byGame) {
  FIELD_TYPES = byGame || {};
}
export function setEnumLabels(byGame) {
  ENUM_LABELS = byGame || {};
}

// a transform entry against a value: a lookup map, or a function for open-ended
// ranges. A miss (no entry, or value the map omits) yields undefined, so prettify
// falls back to the raw value.
export const resolve = (entry, value) =>
  entry == null ? undefined : typeof entry === "function" ? entry(value) : entry[value];

export const prettify = (game, type, key, value) => {
  const t = FIELD_TYPES[game]?.[type]?.[key];
  return resolve(TRANSFORM[t] ?? ENUM_LABELS[game]?.[t], value) ?? value;
};

// a "what is this field" for the tooltip: the curated glossary prose plus the
// field's full value list where it's an enum/Choice/Scale. null when no prose
// is curated — the display affordance means "there's an explanation here".
export const fieldHelp = (game, type, key) => {
  const t = FIELD_TYPES[game]?.[type]?.[key];
  const prose = glossaryProse(type, key, t);
  if (!prose) return null;
  const map = TRANSFORM[t] ?? ENUM_LABELS[game]?.[t];
  if (map && typeof map === "object") {
    const vals = Object.entries(map)
      .sort((a, b) => a[0] - b[0])
      .map(([v, label]) => `${v} = ${label}`)
      .join(", ");
    if (vals) return `${prose}\nValues: ${vals}`;
  }
  return prose;
};

// the field keys to display for a type, given the user's prefs — the "all"
// sentinel or a Set. The one indirection point for the display policy:
//   "all"   -> every field
//   "more"  -> the per-type picks, or the defaults until this type is picked
//              (an explicit empty pick means "show nothing")
//   default -> the type's default set
export function visibleFields(typeName, prefs) {
  const mode = prefs && prefs.mode;
  if (mode === "all") return "all";
  if (mode === "more") {
    const picks = prefs.byType && prefs.byType[typeName];
    return picks ? new Set(picks) : defaultVisible(typeName);
  }
  return defaultVisible(typeName);
}

// [key, displayValue] pairs for a TLV: the semantic nav fields (extra) always,
// then the raw fields the policy admits — prettified, or left as ints when
// prefs.raw is set (a formatting choice; zero-hiding still applies).
export function fieldEntries(t, prefs) {
  const out = [];
  for (const [k, v] of Object.entries(t.extra || {})) if (v !== null && v !== "") out.push([k, v]);
  const show = visibleFields(t.name, prefs);
  if (t.fields)
    for (const [k, v] of Object.entries(t.fields).sort(([a], [b]) => a.localeCompare(b))) {
      if (show !== "all" && !show.has(k)) continue;
      if (v === 0 && HIDE_WHEN_ZERO.has(k)) continue;
      out.push([k, prefs && prefs.raw ? v : prettify(prefs && prefs.game, t.name, k, v)]);
    }
  return out;
}
