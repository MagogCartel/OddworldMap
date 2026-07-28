// DOM-free interpretation of the decoded map data: TLV destinations,
// entry-path analysis, view math and the permalink format. Kept importable in
// bare Node for the unit tests.

import { clamp } from "./util.js";
import {
  ZOOM_MIN,
  ZOOM_MAX,
  FOCUS_ZOOM_MIN,
  FOCUS_ZOOM_MAX,
  FOCUS_SCREENS,
  MAX_ROUTE_PTS,
} from "./config.js";
import { GEO, state, CELL_W, CELL_H } from "./state.js";

export function computeEntryPaths(data, geo = data.geometry) {
  const entries = {};
  const add = (lv, pa) => (entries[lv] ??= new Set()).add(pa);
  for (const L of data.levels)
    for (const P of L.paths)
      for (const t of P.tlvs) {
        const e = t.extra || {};
        const [target, altTarget] = pairTargets(t);
        // a dead destination must not badge a real path
        const arrival = (lv, pa, ca, tgt) => {
          if (!lv || lv === L.short || !pathIn(data, lv, pa)) return;
          if (destTrusted({ lv, pa, ca, target: tgt }, L, data, geo)) add(lv, pa);
        };
        arrival(e.to_level, e.to_path, e.to_cam, target);
        arrival(e.alt_level, e.alt_path, e.alt_cam, altTarget);
        if (t.name === "AbeStart") add(L.short, P.id); // game start / re-entry
      }
  return entries;
}

// the paired object each of a TLV's two destinations lands on, or null where a
// destination names none. Pair number 0 is a number like any other (the
// placeholder ~250 doors and teleporters share — the engine's arrival hunt finds
// the 0-numbered partner). Express wells name the well each ride lands on;
// either well type answers to the id (and the games name local wells
// differently), so that target carries no name
function pairTargets(t) {
  const e = t.extra || {};
  let target = null,
    altTarget = null;
  if (e["target_door#"] != null)
    target = { name: "Door", field: "door#", value: e["target_door#"] };
  else if (e["target_tp#"] != null)
    target = { name: "Teleporter", field: "tp#", value: e["target_tp#"] };
  else if (t.name === "BirdPortal" && e.portal === "travel") target = { name: "BirdPortalExit" };
  if (e["target_well#"] != null) target = { field: "well#", value: e["target_well#"] };
  if (e["alt_target_well#"] != null) altTarget = { field: "well#", value: e["alt_target_well#"] };
  return [target, altTarget];
}

// the path a destination names, or null where the data has no such path
export const pathIn = (data, lv, pa) =>
  data.levels.find((l) => l.short === lv)?.paths.find((p) => p.id === pa) || null;

// whether a destination's named partner is there to be found. A level field the
// designers never set reads as the first level while path and camera keep the
// values that were right for a link inside the source's own level, so a
// cross-level triple needs its partner to corroborate it. Within a level the
// stated camera stands on its own — resolveTarget is camera-bounded and misses
// pairings that are merely unnumbered. A link naming no partner has nothing to
// check and is trusted wherever it points.
export function destTrusted(d, lvl = state.lvl, data = state.data, geo = GEO) {
  if (!d || !d.target) return true;
  const P = pathIn(data, d.lv, d.pa);
  if (!P) return false;
  return d.lv === lvl.short || resolveTarget(d, P, geo) != null;
}

// where a door/portal/well leads: prefers a destination that differs from the
// current level+path unless it names a paired target object
export function destOf(t, lvl = state.lvl, path = state.path, geo = GEO) {
  const e = t.extra || {};
  // hand stones show other cameras rather than transitioning; follow the first
  // view. AO stones carry full level/path/camera triples; AE ones bare camera
  // ids within their own path, where the camera must still exist — a few
  // stones view cameras the shipped path no longer has, and get no follow
  if (e.view1_cam != null) {
    if (e.view1_level != null && e.view1_path != null)
      return { lv: e.view1_level, pa: e.view1_path, ca: e.view1_cam, target: null };
    return lvl && path && camCell(path, e.view1_cam) != null
      ? { lv: lvl.short, pa: path.id, ca: e.view1_cam, target: null }
      : null;
  }
  // paired objects land on their counterpart within the destination camera
  const [target, altTarget] = pairTargets(t);
  const mk = (lv, pa, ca, tgt) => (lv != null && pa != null ? { lv, pa, ca, target: tgt } : null);
  const a = mk(e.to_level, e.to_path, e.to_cam, target);
  const b = mk(e.alt_level, e.alt_path, e.alt_cam, altTarget);
  // a destination is only skippable when it goes nowhere: an untargeted one
  // pointing at the current path, or a well's bounce-back naming the well's
  // own camera (its switch-off state) — a door pair or a well ride to another
  // camera of the same path is a real transition and wins as primary
  const bounce = (d) =>
    lvl &&
    path &&
    d.lv === lvl.short &&
    d.pa === path.id &&
    (d.target != null && d.target.field === "well#"
      ? camCell(path, d.ca) != null && camCell(path, d.ca) === tlvCell(t, path, geo)
      : d.target == null);
  const differs = (d) => d && !bounce(d);
  if (differs(a)) return a;
  if (differs(b)) return b;
  const d = a || b;
  // a well whose every state bounces is a launcher (it exits within its own
  // screen), not self-referencing scenery: the follow keeps no pairing
  return d && d.target != null && d.target.field === "well#" ? { ...d, target: null } : d;
}

// camera id -> grid cell within a path (cam names end in C##)
export function camCell(path, camId) {
  if (camId == null) return null;
  const suffix = "C" + String(camId).padStart(2, "0");
  const cm = path.cams.find((c) => c.name && c.name.endsWith(suffix));
  return cm ? cm.cell : null;
}

// grid cell containing a TLV's top-left corner (spans can cross cells)
export const tlvCell = (t, path, geo) =>
  Math.floor(t.y1 / geo.worldH) * path.w + Math.floor(t.x1 / geo.worldW);

// grid cell under a draw-space point, or null outside the path's grid —
// the margins must not fold into a neighbouring row's edge cell
export function cellAt(x, y, path) {
  const col = Math.floor(x / CELL_W),
    row = Math.floor(y / CELL_H);
  return col >= 0 && col < path.w && row >= 0 && row < path.h ? row * path.w + col : null;
}

// the paired TLV a destination lands on: door numbers are only unique per
// camera, so match inside the destination camera first, path-wide as a fallback.
// Positional targets get no fallback — a name-only target (no pair number)
// resolves only when the stated camera holds exactly one candidate, and pair
// number 0 (shared by many placeholder doors) only inside the stated camera,
// mirroring the engine's forward hunt from there. A nameless target (well ids)
// accepts any object carrying the field, camera-only again: the engine's well
// arrival scan is bounded to the arrival camera's rect.
export function resolveTarget(d, path, geo) {
  if (!d || !d.target) return null;
  const cell = camCell(path, d.ca);
  const match = (t) =>
    (d.target.name == null || t.name === d.target.name) &&
    (d.target.field == null || (t.extra || {})[d.target.field] === d.target.value);
  const positional = d.target.name == null || d.target.field == null || d.target.value === 0;
  if (positional && cell == null) return null;
  if (d.target.field == null) {
    const hits = path.tlvs.filter((t) => match(t) && tlvCell(t, path, geo) === cell);
    return hits.length === 1 ? hits[0] : null;
  }
  return (
    path.tlvs.find((t) => match(t) && (cell == null || tlvCell(t, path, geo) === cell)) ||
    (positional ? null : path.tlvs.find(match)) ||
    null
  );
}

// a paired object (door, teleporter) whose destination names its own camera and
// resolves back to the object itself; a dangling destination whose path-wide
// fallback merely lands on it doesn't count
export function isLoopback(t, lvl = state.lvl, path = state.path, geo = GEO) {
  if (!lvl || !path) return false;
  const d = destOf(t, lvl, path, geo);
  return !!(
    d &&
    d.lv === lvl.short &&
    d.pa === path.id &&
    camCell(path, d.ca) === tlvCell(t, path, geo) &&
    resolveTarget(d, path, geo) === t
  );
}

// consolidated connection edges for the circulation overlay, three shapes:
//   {src, dst, twoWay} — resolved same-path pair (dst is the partner TLV)
//   {src, cell}        — same-path destination without a resolvable partner
//   {src, label}       — off-path destination, labelled "LV Pn"
// Hand-stone views (sights, not transitions), untrusted destinations and
// loopbacks are skipped; a destination that resolves back to its own source
// (dangling camera plus the path-wide fallback) or names a camera missing from
// the grid yields nothing, and neither does one pointing at the source's own
// camera — launcher wells and bounce-backs exit within their screen and must
// not read as arrows.
export function computeConnections(
  lvl = state.lvl,
  path = state.path,
  geo = GEO,
  data = state.data,
) {
  const edges = [];
  const stubs = [];
  const partner = new Map();
  for (const t of path.tlvs) {
    if ((t.extra || {}).view1_cam != null) continue;
    const d = destOf(t, lvl, path, geo);
    if (!d || !destTrusted(d, lvl, data, geo) || isLoopback(t, lvl, path, geo)) continue;
    if (d.lv !== lvl.short || d.pa !== path.id) {
      stubs.push({ src: t, label: `${d.lv} P${d.pa}` });
      continue;
    }
    const g = resolveTarget(d, path, geo);
    if (g && g !== t) {
      partner.set(t, g);
    } else {
      const cell = camCell(path, d.ca);
      if (cell != null && cell !== tlvCell(t, path, geo)) edges.push({ src: t, cell });
    }
  }
  // pairs whose partners resolve to each other merge into one two-way edge;
  // asymmetric chains (stacked double doors, teleporter cycles) stay directed
  const consumed = new Set();
  for (const [t, g] of partner) {
    if (consumed.has(t)) continue;
    if (partner.get(g) === t) {
      edges.push({ src: t, dst: g, twoWay: true });
      consumed.add(g);
    } else {
      edges.push({ src: t, dst: g, twoWay: false });
    }
  }
  return [...edges, ...stubs];
}

// zoom the camera by factor about a fixed canvas point: the world spot under
// (px, py) stays put
export function zoomAt(cam, factor, px, py) {
  const z = clamp(cam.z * factor, ZOOM_MIN, ZOOM_MAX);
  return { x: cam.x + px / cam.z - px / z, y: cam.y + py / cam.z - py / z, z };
}

// a camera and the point at the middle of its viewport, both ways.
export const camCenter = (cam, cw, ch) => ({
  x: cam.x + cw / (2 * cam.z),
  y: cam.y + ch / (2 * cam.z),
  z: cam.z,
});
export const centerCam = (v, cw, ch) => ({
  x: v.x - cw / (2 * v.z),
  y: v.y - ch / (2 * v.z),
  z: v.z,
});

// zoom for jumping to a point: a few screens across, within the focus clamp
export const focusZoom = (cw, ch) =>
  clamp(
    Math.min(cw / (FOCUS_SCREENS * CELL_W), ch / (FOCUS_SCREENS * CELL_H)),
    FOCUS_ZOOM_MIN,
    FOCUS_ZOOM_MAX,
  );

// - permalinks: #GAME/LEVEL/PATH/cx/cy/zoom[/Name@x1,y1][/route=nCOUNT;x,y;…;end] -
// cx/cy is the view's center, not the corner the renderer works in, so a link
// lands on the same spot whatever the size of the window it opens in. Trailing
// segments are matched by shape, not position, and unknown ones are ignored.
export function formatHash(gameId, levelShort, pathId, view, obj, route) {
  let h = `#${gameId}/${levelShort}/${pathId}/${Math.round(view.x)}/${Math.round(view.y)}/${view.z.toFixed(2)}`;
  if (obj) h += `/${obj.name}@${obj.x1},${obj.y1}`;
  if (route?.length) {
    const pairs = route.map((p) => `${Math.round(p.x)},${Math.round(p.y)}`);
    h += `/route=n${route.length};${pairs.join(";")};end`;
  }
  return h;
}

// waypoints from a "route=" payload, "nCOUNT;x,y;…;x,y;end", as the survivors
// plus how many of the count never arrived: a URL shortened in transit keeps
// the legs that made it rather than losing the route whole. The count leads so
// that it outlives the cut; only the trailing marker can prove the payload
// complete, a cut inside the final pair still reading as a well-formed one.
// Both tokens end on a letter or digit, past what autolinkers eat off a URL,
// and the count wears the "n" so that a pair cannot pass for it.
function parseRoute(payload) {
  const tokens = payload.split(";");
  const head = /^n(\d+)$/.exec(tokens[0]);
  const total = head ? +head[1] : 0;
  if (total < 1 || total > MAX_ROUTE_PTS) return null;
  const pairs = tokens.slice(1);
  // the tail goes unread unless it is the marker: a cut leaves either a
  // shortened marker (all pairs arrived) or a pair that may still look whole
  const complete = pairs.pop() === "end";
  if (complete ? pairs.length !== total : pairs.length > total) return null;
  const pts = [];
  for (const pair of pairs) {
    const m = /^(-?\d+),(-?\d+)$/.exec(pair);
    if (!m) return null;
    pts.push({ x: +m[1], y: +m[2] });
  }
  return pts.length ? { pts, lost: total - pts.length } : null;
}

// the TLV a permalink's object segment names, identified by name and origin
// rather than by a list position a rebuild can reorder. Names compare
// case-insensitively, as the game and level codes do.
export const findTlv = (tlvs, obj) =>
  tlvs.find(
    (t) => t.x1 === obj.x1 && t.y1 === obj.y1 && t.name.toLowerCase() === obj.name.toLowerCase(),
  ) || null;

// the viewer escapes nothing — every delimiter it writes is legal in a fragment
// bare — but share widgets and mail clients percent-encode one anyway. A stray
// % that isn't an escape leaves the fragment as it found it.
function decodeFragment(h) {
  if (!h.includes("%")) return h;
  try {
    return decodeURIComponent(h);
  } catch {
    return h;
  }
}

// the view is all-or-nothing: an incomplete or unreadable trio yields none at
// all, so the caller fits the path rather than centering on a NaN
const finiteView = (x, y, z) =>
  Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z) && z > 0 ? { x, y, z } : null;

// null for an empty hash; view is the center point plus zoom, null unless all
// three read; obj names a TLV to highlight, identified by name and origin;
// route is a list of draw-space waypoints, routeLost how many of them a
// shortened URL never delivered. game/level/path may still come back empty or
// NaN — the caller resolves those against the data.
export function parseHash(hash) {
  const h = decodeFragment(hash.replace(/^#/, ""));
  if (!h) return null;
  const parts = h.split("/");
  const segs = parts.slice(6);
  const om = segs.map((s) => /^(\w+)@(-?\d+),(-?\d+)$/.exec(s)).find(Boolean);
  const rt = segs.find((s) => s.startsWith("route="));
  const route = rt ? parseRoute(rt.slice(6)) : null;
  return {
    game: parts[0].toUpperCase(),
    level: (parts[1] || "").toUpperCase(),
    path: +parts[2],
    view: parts.length >= 6 ? finiteView(+parts[3], +parts[4], +parts[5]) : null,
    obj: om ? { name: om[1], x1: +om[2], y1: +om[3] } : null,
    route: route ? route.pts : null,
    routeLost: route ? route.lost : 0,
  };
}
