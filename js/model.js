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

export function computeEntryPaths(data) {
  const entries = {};
  const add = (lv, pa) => {
    if (lv != null && pa != null) (entries[lv] ??= new Set()).add(pa);
  };
  for (const L of data.levels)
    for (const P of L.paths)
      for (const t of P.tlvs) {
        const e = t.extra || {};
        if (e.to_level && e.to_level !== L.short) add(e.to_level, e.to_path);
        if (e.alt_level && e.alt_level !== L.short) add(e.alt_level, e.alt_path);
        if (t.name === "AbeStart") add(L.short, P.id); // game start / re-entry
      }
  return entries;
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
  // paired objects land on their counterpart within the destination camera;
  // 0 is a pair number like any other (the placeholder ~250 doors and
  // teleporters share — the engine's arrival hunt finds the 0-numbered partner)
  let target = null;
  let altTarget = null;
  if (e["target_door#"] != null)
    target = { name: "Door", field: "door#", value: e["target_door#"] };
  else if (e["target_tp#"] != null)
    target = { name: "Teleporter", field: "tp#", value: e["target_tp#"] };
  else if (t.name === "BirdPortal" && e.portal === "travel") target = { name: "BirdPortalExit" };
  // express wells name the well each ride lands on; either well type answers
  // to the id (and the games name local wells differently), so the target
  // carries no name
  if (e["target_well#"] != null) target = { field: "well#", value: e["target_well#"] };
  if (e["alt_target_well#"] != null) altTarget = { field: "well#", value: e["alt_target_well#"] };
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
// Hand-stone views (sights, not transitions) and loopbacks are skipped; a
// destination that resolves back to its own source (dangling camera plus the
// path-wide fallback) or names a camera missing from the grid yields nothing,
// and neither does one pointing at the source's own camera — launcher wells
// and bounce-backs exit within their screen and must not read as arrows.
export function computeConnections(lvl = state.lvl, path = state.path, geo = GEO) {
  const edges = [];
  const stubs = [];
  const partner = new Map();
  for (const t of path.tlvs) {
    if ((t.extra || {}).view1_cam != null) continue;
    const d = destOf(t, lvl, path, geo);
    if (!d || isLoopback(t, lvl, path, geo)) continue;
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

// the view for jumping to a point: centered on it, a few screens across
export function focusView(fx, fy, cw, ch) {
  const z = clamp(
    Math.min(cw / (FOCUS_SCREENS * CELL_W), ch / (FOCUS_SCREENS * CELL_H)),
    FOCUS_ZOOM_MIN,
    FOCUS_ZOOM_MAX,
  );
  return { x: fx - cw / (2 * z), y: fy - ch / (2 * z), z };
}

// ---- permalinks: #GAME/LEVEL/PATH/x/y/zoom[/Name@x1,y1][/route=x1,y1;…] ----
// Trailing segments are matched by shape, not position, and unknown ones are
// ignored, so old viewers tolerate new segments and vice versa.
export function formatHash(gameId, levelShort, pathId, cam, obj, route) {
  let h = `#${gameId}/${levelShort}/${pathId}/${Math.round(cam.x)}/${Math.round(cam.y)}/${cam.z.toFixed(2)}`;
  if (obj) h += `/${obj.name}@${obj.x1},${obj.y1}`;
  if (route?.length)
    h += `/route=${route.map((p) => `${Math.round(p.x)},${Math.round(p.y)}`).join(";")}`;
  return h;
}

// route waypoints from a "route=" payload: all-or-nothing, so a truncated URL
// yields no route rather than a silently shortened one
function parseRoute(payload) {
  const pairs = payload.split(";");
  if (!payload || pairs.length > MAX_ROUTE_PTS) return null;
  const pts = [];
  for (const pair of pairs) {
    const m = /^(-?\d+),(-?\d+)$/.exec(pair);
    if (!m) return null;
    pts.push({ x: +m[1], y: +m[2] });
  }
  return pts;
}

// null for an empty hash; view is null unless x/y/z are all present; obj names
// a TLV to highlight, identified by name and origin; route is a list of
// draw-space waypoints. Numbers may come back NaN — the caller resolves and
// validates against the data.
export function parseHash(hash) {
  const h = hash.replace(/^#/, "");
  if (!h) return null;
  const parts = h.split("/");
  const segs = parts.slice(6);
  const om = segs.map((s) => /^(\w+)@(-?\d+),(-?\d+)$/.exec(s)).find(Boolean);
  const rt = segs.find((s) => s.startsWith("route="));
  return {
    game: parts[0].toUpperCase(),
    level: (parts[1] || "").toUpperCase(),
    path: +parts[2],
    view:
      parts[3] != null && parts.length >= 6 ? { x: +parts[3], y: +parts[4], z: +parts[5] } : null,
    obj: om ? { name: om[1], x1: +om[2], y1: +om[3] } : null,
    route: rt ? parseRoute(rt.slice(6)) : null,
  };
}
