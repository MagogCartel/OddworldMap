// Selection (game/level/path), follow-to-destination, view fitting and hash permalinks.
// Fires a "selection-changed" window event (detail.fromHash) whenever a path is picked.

import { clamp, esc } from "./util.js";
import { ZOOM_MIN, ZOOM_MAX } from "./config.js";
import { $, cv, gameBtns, levelBtns, pathBtns } from "./dom.js";
import { toast } from "./toast.js";
import {
  state,
  GEO,
  CELL_W,
  CELL_H,
  cellOrigin,
  setGeometry,
  setSpacing,
  dX,
  dY,
  wX,
  wY,
} from "./state.js";
import { draw, flashAt } from "./render.js";
import {
  camCell,
  camCenter,
  centerCam,
  computeEntryPaths,
  findTlv,
  focusZoom,
  formatHash,
  hashToDraw,
  markerCentre,
  parseHash,
  resolveTarget,
} from "./model.js";
import { pathDisplayName, pathNickname } from "./annotations.js";
import { isDemoPath, pathVisible, revealPath } from "./demo.js";
import { orderPaths } from "./pathorder.js";
import { displayLabel, getSettings, rememberLocation } from "./settings.js";

function markOn(box, key) {
  for (const b of box.children) b.classList.toggle("on", b.dataset.key === key);
}

// the button's label, composed from what it carries and the full-names
// setting; re-run on every button when the setting flips
function setLabel(b) {
  const on = getSettings().fullNames;
  const label = esc(displayLabel(b.dataset.code, b.dataset.full, on));
  const nick = on ? b.dataset.nickname : "";
  b.innerHTML = nick ? `${label} <span class="nickname">· ${esc(nick)}</span>` : label;
}

window.addEventListener("settings-changed", (e) => {
  if (e.detail.key !== "fullNames") return;
  for (const box of [gameBtns, levelBtns, pathBtns]) for (const b of box.children) setLabel(b);
});

// build the game buttons once the datasets are known
export function initGames(games) {
  state.games = games;
  games.forEach((G) => {
    const b = document.createElement("button");
    b.dataset.code = G.id;
    b.dataset.full = G.game;
    setLabel(b);
    b.title = G.game;
    b.dataset.key = G.id;
    b.onclick = () => selectGame(G);
    gameBtns.appendChild(b);
  });
}

export function selectGame(G, keepView) {
  state.data = G;
  setGeometry(G.geometry);
  setSpacing(state.show.spaced);
  markOn(gameBtns, G.id);
  $("gameName").textContent = G.game;
  state.entry = computeEntryPaths(G);
  levelBtns.innerHTML = "";
  G.levels.forEach((L) => {
    const b = document.createElement("button");
    b.dataset.code = L.short;
    b.dataset.full = L.name;
    setLabel(b);
    b.title = L.name;
    b.dataset.key = L.short;
    b.onclick = () => selectLevel(L);
    levelBtns.appendChild(b);
  });
  if (!keepView && G.levels.length) selectLevel(G.levels[0]);
}

const visiblePaths = (L) => {
  const ps = L.paths.filter(pathVisible);
  return getSettings().playOrder ? orderPaths(state.data, L, ps) : ps;
};

function buildPathButtons() {
  const L = state.lvl;
  pathBtns.innerHTML = "";
  visiblePaths(L).forEach((P) => {
    const b = document.createElement("button");
    const name = pathDisplayName(state.data.id, L.short, P);
    const nickname = pathNickname(state.data.id, L.short, P);
    b.dataset.code = "P" + P.id;
    b.dataset.full = name || "";
    if (nickname) b.dataset.nickname = nickname;
    setLabel(b);
    b.dataset.key = String(P.id);
    const tip = [];
    if (P.section) tip.push(P.section);
    // one pairing, one separator: the tooltip reads it the way the face does
    const named = [name, nickname].filter(Boolean).join(" · ");
    if (named) tip.push(named);
    if (state.entry[L.short] && state.entry[L.short].has(P.id)) {
      b.classList.add("entry");
      tip.push("entry point (arrived at from another level)");
    }
    if (isDemoPath(P)) tip.push("demo path (only the title-screen demos play here)");
    if (tip.length) b.title = tip.join(" — ");
    b.onclick = () => selectPath(P);
    pathBtns.appendChild(b);
  });
  if (state.path) markOn(pathBtns, String(state.path.id));
}

// the level-switch half alone, no path selected: a caller that knows its
// target path selects it itself, in one selection change — an intermediate
// default-path selection would fire listeners against a path nobody chose
function setLevel(L) {
  state.lvl = L;
  markOn(levelBtns, L.short);
  buildPathButtons();
}

function selectLevel(L) {
  setLevel(L);
  const first = visiblePaths(L)[0] ?? L.paths[0];
  if (first) selectPathById(first.id);
}

window.addEventListener("settings-changed", (e) => {
  if (e.detail.key !== "demoPaths" || !state.lvl) return;
  if (state.path) revealPath(state.path); // hiding the class must not unlist the path in hand
  buildPathButtons();
});

window.addEventListener("settings-changed", (e) => {
  if (e.detail.key !== "playOrder" || !state.lvl) return;
  buildPathButtons();
});

function selectPath(P) {
  state.path = P;
  markOn(pathBtns, String(P.id));
  fitView();
  draw();
  scheduleHash(true);
  window.dispatchEvent(
    new CustomEvent("selection-changed", { detail: { fromHash: applyingHash } }),
  );
}

function selectPathById(id) {
  const P = state.lvl.paths.find((p) => p.id === id);
  if (!P) return false;
  if (revealPath(P)) buildPathButtons(); // a hidden path arrives with no button of its own
  selectPath(P);
  return true;
}

// the [ / ] shortcuts: step through the current level's paths, wrapping
export function cyclePath(dir) {
  if (!state.lvl) return;
  const paths = visiblePaths(state.lvl);
  selectPath(paths[(paths.indexOf(state.path) + dir + paths.length) % paths.length]);
}

let camToken = 0; // bumped on explicit positioning to invalidate pending fits

function fitView() {
  const token = ++camToken;
  const attempt = () => {
    if (token !== camToken) return; // superseded by hash restore or follow
    if (!cv.clientWidth || !cv.clientHeight) {
      requestAnimationFrame(attempt);
      return;
    }
    const [ox, oy] = cellOrigin();
    const w = state.path.w * CELL_W,
      h = state.path.h * CELL_H;
    const zx = cv.clientWidth / (w + 200),
      zy = cv.clientHeight / (h + 200);
    state.cam.z = Math.max(ZOOM_MIN, Math.min(zx, zy));
    state.cam.x = ox - (cv.clientWidth / state.cam.z - w) / 2;
    state.cam.y = oy - (cv.clientHeight / state.cam.z - h) / 2;
    draw();
  };
  attempt();
}

// put (fx, fy) at the middle of the viewport, at zoom z or the focus zoom when
// z is null. Waits on layout like fitView: the corner comes from the canvas size
function centerOn(fx, fy, z) {
  const token = ++camToken; // cancel any fit still waiting on layout
  const attempt = () => {
    if (token !== camToken) return;
    const cw = cv.clientWidth,
      ch = cv.clientHeight;
    if (!cw || !ch) {
      requestAnimationFrame(attempt);
      return;
    }
    Object.assign(state.cam, centerCam({ x: fx, y: fy, z: z ?? focusZoom(cw, ch) }, cw, ch));
    draw();
  };
  attempt();
}

// center on (fx, fy) zoomed to a few screens across, flash the spot
function focusOn(fx, fy) {
  centerOn(fx, fy, null);
  flashAt(fx, fy);
  scheduleHash(true);
}

// permalink to one object: the focused view plus the object identity, so
// opening the link can highlight it
export function objectHash(t) {
  const [fx, fy] = markerCentre(t);
  const v = { x: fx, y: fy, z: focusZoom(cv.clientWidth, cv.clientHeight) };
  return formatHash(state.data.id, state.lvl.short, state.path.id, v, t, state.route);
}

// ---- follow (click a door/portal/well to jump to its destination) -----
export function navigateToDest(d) {
  if (!cv.clientWidth) {
    requestAnimationFrame(() => navigateToDest(d));
    return;
  }
  const L = state.data.levels.find((l) => l.short === d.lv);
  if (!L) return;
  if (state.lvl !== L) setLevel(L);
  if (!selectPathById(d.pa)) return;

  let fx = null,
    fy = null;
  const tgt = resolveTarget(d, state.path, GEO);
  if (tgt) {
    [fx, fy] = markerCentre(tgt);
  }
  const cell = camCell(state.path, d.ca);
  if (fx == null && cell != null) {
    fx = (cell % state.path.w) * CELL_W + GEO.visW / 2;
    fy = Math.floor(cell / state.path.w) * CELL_H + GEO.visH / 2;
  }
  if (fx == null) return; // path-level target: selectPath already fit the view
  focusOn(fx, fy);
}

export function jumpToTlv(G, L, P, t) {
  if (state.data !== G) selectGame(G, true);
  if (state.lvl !== L) setLevel(L);
  if (state.path !== P) selectPathById(P.id);
  focusOn(...markerCentre(t));
}

// a whole place: one path, a level (which opens on the first path it lists),
// or one screen of a path, centered when a camera id is named
export function jumpToPlace(G, L, P, cam) {
  if (state.data !== G) selectGame(G, true);
  if (!P) {
    selectLevel(L);
    return;
  }
  if (state.lvl !== L) setLevel(L);
  selectPathById(P.id);
  if (cam == null) return;
  const cell = camCell(state.path, cam);
  if (cell != null)
    focusOn(
      (cell % state.path.w) * CELL_W + GEO.visW / 2,
      Math.floor(cell / state.path.w) * CELL_H + GEO.visH / 2,
    );
}

// ---- permalinks ---------------------------------------------------------
let applyingHash = false,
  hashTimer = null,
  hashPush = false; // a requested history entry survives later replace requests

// ---- pitch ---------------------------------------------------------------

// Spacing the screens out or packing them back moves every draw coordinate, so
// what the viewer holds in draw space is carried across by the world points it
// stands for: the view's centre (not its corner, which would slide the view),
// the ruler's ends and every route waypoint. The flip happens between the two
// halves, which is why they are read out and put back here rather than inside
// setSpacing.
export function setPitch(on) {
  const cw = cv.clientWidth,
    ch = cv.clientHeight;
  const world = (p) => ({ x: wX(p.x), y: wY(p.y) });
  const centre = world(camCenter(state.cam, cw, ch));
  const ruler = state.ruler && {
    a: world({ x: state.ruler.x1, y: state.ruler.y1 }),
    b: world({ x: state.ruler.x2, y: state.ruler.y2 }),
  };
  const route = state.route?.map((s) => ({ ...s, pts: s.pts.map(world) }));

  if (!setSpacing(on)) return;

  Object.assign(state.cam, centerCam({ ...toDraw(centre), z: state.cam.z }, cw, ch));
  if (ruler) {
    const [a, b] = [toDraw(ruler.a), toDraw(ruler.b)];
    state.ruler = { x1: a.x, y1: a.y, x2: b.x, y2: b.y };
  }
  if (route) state.route = route.map((s) => ({ ...s, pts: s.pts.map(toDraw) }));
  scheduleHash(false);
  draw();
}
const toDraw = (p) => ({ x: dX(p.x), y: dY(p.y) });

// embeds sit in other people's pages: browsing one must not move the
// visitor's remembered location
const inEmbed = () => document.body.classList.contains("embed");

// permalink to the current view (what the address bar shows once the
// debounced hash write lands)
export function viewHash() {
  const v = camCenter(state.cam, cv.clientWidth, cv.clientHeight);
  return formatHash(state.data.id, state.lvl.short, state.path.id, v, null, state.route);
}

function writeHash(push) {
  hashTimer = null;
  hashPush = false;
  // every pan, zoom and selection settles through here, debounced
  window.dispatchEvent(new CustomEvent("view-changed"));
  const h = viewHash();
  if (!inEmbed()) rememberLocation(h);
  if (h === location.hash) return;
  if (push)
    location.hash = h; // history entry (level/path/follow)
  else history.replaceState(null, "", h); // silent update (pan/zoom)
}

// each call reschedules the one pending write; push-ness is sticky until it
// fires, so a follow's history entry can't be downgraded by the quick silent
// writes that ride on its heels
export function scheduleHash(push) {
  if (applyingHash || !state.path) return;
  hashPush ||= push;
  clearTimeout(hashTimer);
  hashTimer = setTimeout(() => writeHash(hashPush), hashPush ? 0 : 350);
}

// a pending write fires now: the entry a follow is about to leave behind
// should hold what the eye last saw, not what last settled
export function flushHash() {
  if (hashTimer == null) return;
  clearTimeout(hashTimer);
  writeHash(hashPush);
}

// the entry a dialog leaves behind has to hold the settled view, or the back
// press that closes it would undo a pan as well
window.addEventListener("dialog-opened", flushHash);

export function applyHash() {
  const p = parseHash(location.hash);
  if (!p) return false;
  const G = state.games.find((g) => g.id === p.game);
  if (!G) return false;
  const L = G.levels.find((l) => l.short === p.level);
  if (!L) return false;
  applyingHash = true;
  if (state.data !== G) selectGame(G, true);
  if (state.lvl !== L) selectLevel(L);
  if (!selectPathById(p.path)) {
    applyingHash = false;
    return false;
  }
  // the geometry is the link's own from here, which is what world coordinates
  // in it are waiting on
  const { view, route } = hashToDraw(p);
  if (view) centerOn(view.x, view.y, clamp(view.z, ZOOM_MIN, ZOOM_MAX));
  applyingHash = false;
  if (p.obj) {
    // a link to a specific object: center it and hold a marker on it
    const t = findTlv(state.path.tlvs, p.obj);
    const c = t && markerCentre(t);
    const fx = c ? c[0] : (view?.x ?? dX(p.obj.x1)),
      fy = c ? c[1] : (view?.y ?? dY(p.obj.y1));
    centerOn(fx, fy, null); // re-derives the focus zoom for this viewport
    flashAt(fx, fy, true);
    toast(t ? `marker on ${t.name}` : `no ${p.obj.name} at that spot`);
  }
  state.route = route; // the hash is the source of truth: absent means no route
  if (p.routeLost) {
    const arrived = p.route.reduce((n, s) => n + s.pts.length, 0);
    toast(`route link cut short: ${arrived} of ${arrived + p.routeLost} waypoints`);
  }
  window.dispatchEvent(new CustomEvent("route-changed"));
  draw();
  return true;
}

window.addEventListener("hashchange", () => {
  if (applyingHash) return;
  // back/forward retraces update the remembered spot; a rejected hash must not
  if (applyHash() && !inEmbed()) rememberLocation(location.hash);
});
