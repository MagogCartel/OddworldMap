// Edits to the shipped data as a local sandbox. An edit is a per-field delta
// keyed by the object's pristine origin; a path carrying deltas stands in the
// dataset as a new object built over the pristine one, its unedited TLVs kept by
// identity and its edited ones fresh, with their navigation bucket derived
// again; a path whose deltas are all gone stands as the pristine object itself.
// Nothing here writes into a fetched object. Importable in bare Node: no DOM.

import { state } from "./state.js";
import { deriveExtra } from "./extra.js";
import { pathVisible, revealPath } from "./demo.js";
import { invalidateEntry } from "./pathorder.js";
import { valueMap } from "./fields.js";

const S16_MIN = -32768,
  S16_MAX = 32767;

// per game: the level-id -> short map a destination's level reads through
const LEVEL_SHORT = {};
export const setLevelShort = (gameId, map) => {
  LEVEL_SHORT[gameId] = map;
};
export const hasLevelShort = (gameId) => gameId in LEVEL_SHORT;

// an embed is someone else's page showing this map, so it shows the shipped one
let enabled = true;
export const setEnabled = (on) => {
  enabled = on;
};

// {game: {"LV/PA": {objects: {key: {fields: {name: value}}}}}}
let edits = {};
export const restoreEdits = (all) => {
  edits = all;
};
export const editStore = () => edits;

const pathKey = (lv, pa) => `${lv}/${pa}`;

// a pristine path's objects by origin: name and top-left, with an ordinal where
// the tuple repeats inside the path, so a delta names one object and not the first
// of several
const keysOf = new WeakMap();
export function objectKeys(pristinePath) {
  let m = keysOf.get(pristinePath);
  if (m) return m;
  const count = new Map();
  for (const t of pristinePath.tlvs) {
    const k = `${t.name}@${t.x1},${t.y1}`;
    count.set(k, (count.get(k) || 0) + 1);
  }
  const seen = new Map();
  m = new Map();
  for (const t of pristinePath.tlvs) {
    const k = `${t.name}@${t.x1},${t.y1}`;
    if (count.get(k) === 1) m.set(t, k);
    else {
      const n = (seen.get(k) || 0) + 1;
      seen.set(k, n);
      m.set(t, `${k}#${n}`);
    }
  }
  keysOf.set(pristinePath, m);
  return m;
}
export const objectKey = (pristinePath, t) => objectKeys(pristinePath).get(t) ?? null;

// a materialized TLV -> the pristine one and the delta it carries
const origin = new WeakMap();
// the paths standing as deltas
const edited = new WeakSet();
// what stood in a dataset before a swap: per dataset, its levels and paths by place
const pristine = new WeakMap();
function shipped(G) {
  let r = pristine.get(G);
  if (!r) pristine.set(G, (r = { levels: new Map(), paths: new Map() }));
  return r;
}

export const pristineOf = (t) => origin.get(t)?.pristine ?? t;
export const editedFields = (t) => origin.get(t)?.delta.fields ?? {};
export const pathEdited = (path) => edited.has(path);

// the object now standing in `path` for a pristine or stale TLV
export function currentOf(t, path = state.path) {
  const p = pristineOf(t);
  if (!path) return null;
  return path.tlvs.find((c) => c === p || origin.get(c)?.pristine === p) ?? null;
}

export const hasStoredEdits = (gameId) => enabled && Object.keys(edits[gameId] ?? {}).length > 0;

export function gameEdits(gameId) {
  let objects = 0,
    paths = 0;
  for (const pe of Object.values(edits[gameId] ?? {})) {
    const n = Object.keys(pe.objects).length;
    if (n) paths++;
    objects += n;
  }
  return { objects, paths };
}

// the one rule a delta answers to, entered or restored: a field the object has,
// and either the value it shipped with or an integer the archive's word can hold,
// labelled where labels exist
export function validDelta(gameId, pristine, field, value) {
  if (!pristine.fields || !(field in pristine.fields)) return false;
  if (value === pristine.fields[field]) return true;
  if (!Number.isInteger(value) || value < S16_MIN || value > S16_MAX) return false;
  const map = valueMap(gameId, pristine.name, field);
  return !map || map[value] !== undefined;
}

// the path as its deltas make it: the pristine object itself when there are none
export function materializePath(gameId, pristine, pathEdits) {
  const objects = pathEdits?.objects ?? {};
  const live = Object.entries(objects).filter(([, d]) => Object.keys(d.fields ?? {}).length);
  if (!live.length) return pristine;
  if (!hasLevelShort(gameId))
    throw new Error(`${gameId}: no level map to derive destinations with`);
  const keys = objectKeys(pristine);
  const byKey = new Map(live);
  const tlvs = pristine.tlvs.map((t) => {
    const delta = byKey.get(keys.get(t));
    if (!delta) return t;
    const fields = { ...t.fields, ...delta.fields };
    const fresh = {
      ...t,
      fields,
      extra: deriveExtra(gameId, { ...t, fields }, LEVEL_SHORT[gameId]),
    };
    // the delta as materialized, not the live entry a later step writes into
    origin.set(fresh, { pristine: t, delta: JSON.parse(JSON.stringify(delta)) });
    return fresh;
  });
  const fresh = { ...pristine, tlvs };
  edited.add(fresh);
  return fresh;
}

// the level as the store makes it, over the pristine level and paths recorded
// the first time each was replaced
function rebuildLevel(G, j) {
  const L = G.levels[j];
  const was = shipped(G);
  if (!was.levels.has(L.short)) was.levels.set(L.short, L);
  const PL = was.levels.get(L.short);
  const paths = PL.paths.map((P, i) => {
    const pk = pathKey(L.short, P.id);
    if (!was.paths.has(pk)) was.paths.set(pk, P);
    const fresh = materializePath(G.id, was.paths.get(pk), edits[G.id]?.[pk]);
    // a path already standing as these deltas keeps its identity
    const standing = L.paths[i];
    return standing !== was.paths.get(pk) && sameDeltas(standing, fresh) ? standing : fresh;
  });
  return paths.every((P, i) => P === PL.paths[i]) ? PL : { ...PL, paths };
}

// two materializations of one path over equal deltas draw the same
const sameDeltas = (a, b) =>
  a.tlvs.length === b.tlvs.length &&
  a.tlvs.every((t, i) => {
    const u = b.tlvs[i];
    if (t === u) return true;
    const da = origin.get(t),
      db = origin.get(u);
    return (
      da &&
      db &&
      da.pristine === db.pristine &&
      JSON.stringify(da.delta) === JSON.stringify(db.delta)
    );
  });

// every swap, in either direction, goes through here: the dataset takes the
// level, the selection follows it, a demo path's reveal survives, the game-wide
// memos let go, and the page is told
export function swapLevel(G, j, L2, pa) {
  const old = G.levels[j];
  G.levels[j] = L2;
  old.paths.forEach((P, i) => {
    if (P !== L2.paths[i] && pathVisible(P)) revealPath(L2.paths[i]);
  });
  if (state.data === G && state.lvl?.short === L2.short) {
    state.lvl = L2;
    if (state.path) state.path = L2.paths.find((P) => P.id === state.path.id) ?? null;
    if (state.sel) state.sel = currentOf(state.sel, state.path);
  }
  invalidateEntry(G);
  if (typeof window !== "undefined")
    window.dispatchEvent(
      new CustomEvent("data-changed", { detail: { game: G.id, lv: L2.short, pa } }),
    );
}

function swapPath(G, lv, pa) {
  const j = G.levels.findIndex((L) => L.short === lv);
  if (j < 0) return;
  swapLevel(G, j, rebuildLevel(G, j), pa);
}

const gameOf = (gameId) => state.games.find((g) => g.id === gameId) ?? null;

// one field of one object, on the path in hand; the value it had shipped with
// takes the delta away again. Returns the object now standing for it.
export function applyFieldEdit(t, field, value, where = {}) {
  const gameId = where.game ?? state.data.id,
    lv = where.lv ?? state.lvl.short,
    pa = where.pa ?? state.path.id;
  const G = gameOf(gameId);
  const pristine = pristineOf(t);
  if (!hasLevelShort(gameId))
    throw new Error(`${gameId}: no level map to derive destinations with`);
  if (!validDelta(gameId, pristine, field, value))
    throw new Error(`${pristine.name}.${field}: ${value} is not a value the archive holds`);
  const pk = pathKey(lv, pa);
  const P =
    shipped(G).paths.get(pk) ?? G.levels.find((L) => L.short === lv).paths.find((p) => p.id === pa);
  const key = objectKey(P, pristine);
  if (!key) throw new Error(`${pristine.name} is not on ${lv} P${pa}`);
  const game = (edits[gameId] ??= {});
  const path = (game[pk] ??= { objects: {} });
  const delta = (path.objects[key] ??= { fields: {} });
  if (value === pristine.fields[field]) delete delta.fields[field];
  else delta.fields[field] = value;
  if (!Object.keys(delta.fields).length) delete path.objects[key];
  if (!Object.keys(path.objects).length) delete game[pk];
  if (!Object.keys(game).length) delete edits[gameId];
  swapPath(G, lv, pa);
  return currentOf(
    pristine,
    G.levels.find((L) => L.short === lv).paths.find((p) => p.id === pa),
  );
}

export function revertPath(gameId, lv, pa) {
  const game = edits[gameId];
  if (!game?.[pathKey(lv, pa)]) return;
  delete game[pathKey(lv, pa)];
  if (!Object.keys(game).length) delete edits[gameId];
  const G = gameOf(gameId);
  if (G) swapPath(G, lv, pa);
}

export function forgetAll() {
  const all = edits;
  edits = {};
  for (const [gameId, game] of Object.entries(all)) {
    const G = gameOf(gameId);
    if (!G) continue;
    for (const pk of Object.keys(game)) {
      const [lv, pa] = pk.split("/");
      swapPath(G, lv, +pa);
    }
  }
}

// the stored deltas over a dataset that has not reached the page yet: each is
// applied where it still answers to its object and dropped where it does not,
// a delta the disc has caught up with among the dropped (it no longer differs,
// and could never be taken away field by field), and the count of both waits
// for the page to say it
const reports = new Map();
export function applyStoredEdits(G) {
  let applied = 0,
    dropped = 0;
  const game = edits[G.id] ?? {};
  for (const [pk, pe] of Object.entries(game)) {
    const [lv, pa] = pk.split("/");
    const L = G.levels.find((l) => l.short === lv);
    const P = L?.paths.find((p) => p.id === +pa);
    const byKey = P && new Map([...objectKeys(P)].map(([t, k]) => [k, t]));
    for (const [key, delta] of Object.entries(pe.objects)) {
      const t = byKey?.get(key);
      for (const [field, value] of Object.entries(delta.fields ?? {})) {
        if (t && validDelta(G.id, t, field, value) && value !== t.fields[field]) applied++;
        else {
          dropped++;
          delete delta.fields[field];
        }
      }
      if (!t || !Object.keys(delta.fields ?? {}).length) delete pe.objects[key];
    }
    if (!Object.keys(pe.objects).length) delete game[pk];
  }
  if (!Object.keys(game).length) delete edits[G.id];
  if (applied)
    G.levels.forEach((L, j) => {
      if (Object.keys(game).some((pk) => pk.startsWith(`${L.short}/`)))
        G.levels[j] = rebuildLevel(G, j);
    });
  reports.set(G.id, { applied, dropped });
  return { applied, dropped };
}

export function takeReport(gameId) {
  const r = reports.get(gameId) ?? null;
  reports.delete(gameId);
  return r;
}
