// Selection (game/level/path), follow-to-destination, view fitting and hash permalinks.
// Fires a "selection-changed" window event (detail.fromHash) whenever a path is picked.

import { clamp, esc } from "./util.js";
import { ZOOM_MIN, ZOOM_MAX } from "./config.js";
import { $, cv, gameBtns, levelBtns, pathBtns } from "./dom.js";
import { toast } from "./toast.js";
import { state, GEO, CELL_W, CELL_H, setGeometry, dX, dY } from "./state.js";
import { draw, flashAt } from "./render.js";
import {
  camCell,
  camCenter,
  centerCam,
  computeEntryPaths,
  findTlv,
  focusZoom,
  formatHash,
  parseHash,
  resolveTarget,
} from "./model.js";
import { pathDisplayName, pathNickname } from "./annotations.js";
import { isDemoPath, pathVisible, revealPath } from "./demo.js";
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

const visiblePaths = (L) => L.paths.filter(pathVisible);

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

function selectLevel(L) {
  state.lvl = L;
  markOn(levelBtns, L.short);
  buildPathButtons();
  const first = visiblePaths(L)[0] ?? L.paths[0];
  if (first) selectPathById(first.id);
}

window.addEventListener("settings-changed", (e) => {
  if (e.detail.key !== "demoPaths" || !state.lvl) return;
  if (state.path) revealPath(state.path); // hiding the class must not unlist the path in hand
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
    const w = state.path.w * CELL_W,
      h = state.path.h * CELL_H;
    const zx = cv.clientWidth / (w + 200),
      zy = cv.clientHeight / (h + 200);
    state.cam.z = Math.max(ZOOM_MIN, Math.min(zx, zy));
    state.cam.x = -(cv.clientWidth / state.cam.z - w) / 2;
    state.cam.y = -(cv.clientHeight / state.cam.z - h) / 2;
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
  const fx = (dX(t.x1) + dX(t.x2)) / 2,
    fy = (dY(t.y1) + dY(t.y2)) / 2;
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
  if (state.lvl !== L) selectLevel(L);
  if (!selectPathById(d.pa)) return;

  let fx = null,
    fy = null;
  const tgt = resolveTarget(d, state.path, GEO);
  if (tgt) {
    fx = (dX(tgt.x1) + dX(tgt.x2)) / 2;
    fy = (dY(tgt.y1) + dY(tgt.y2)) / 2;
  }
  const cell = camCell(state.path, d.ca);
  if (fx == null && cell != null) {
    fx = (cell % state.path.w) * CELL_W + CELL_W / 2;
    fy = Math.floor(cell / state.path.w) * CELL_H + CELL_H / 2;
  }
  if (fx == null) return; // path-level target: selectPath already fit the view
  focusOn(fx, fy);
}

export function jumpToTlv(G, L, P, t) {
  if (state.data !== G) selectGame(G, true);
  if (state.lvl !== L) selectLevel(L);
  if (state.path !== P) selectPathById(P.id);
  focusOn((dX(t.x1) + dX(t.x2)) / 2, (dY(t.y1) + dY(t.y2)) / 2);
}

// a whole place: one path, or a level, which opens on the first path it lists
export function jumpToPlace(G, L, P) {
  if (state.data !== G) selectGame(G, true);
  if (!P || state.lvl !== L) selectLevel(L);
  if (P) selectPathById(P.id);
}

// ---- permalinks ---------------------------------------------------------
let applyingHash = false,
  hashTimer = null;

// embeds sit in other people's pages: browsing one must not move the
// visitor's remembered location
const inEmbed = () => document.body.classList.contains("embed");

// permalink to the current view (what the address bar shows once the
// debounced hash write lands)
export function viewHash() {
  const v = camCenter(state.cam, cv.clientWidth, cv.clientHeight);
  return formatHash(state.data.id, state.lvl.short, state.path.id, v, null, state.route);
}

export function scheduleHash(push) {
  if (applyingHash || !state.path) return;
  clearTimeout(hashTimer);
  hashTimer = setTimeout(
    () => {
      const h = viewHash();
      if (!inEmbed()) rememberLocation(h);
      if (h === location.hash) return;
      if (push)
        location.hash = h; // history entry (level/path/follow)
      else history.replaceState(null, "", h); // silent update (pan/zoom)
    },
    push ? 0 : 350,
  );
}

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
  if (p.view) centerOn(p.view.x, p.view.y, clamp(p.view.z, ZOOM_MIN, ZOOM_MAX));
  applyingHash = false;
  if (p.obj) {
    // a link to a specific object: center it and hold a marker on it
    const t = findTlv(state.path.tlvs, p.obj);
    const fx = t ? (dX(t.x1) + dX(t.x2)) / 2 : (p.view?.x ?? dX(p.obj.x1)),
      fy = t ? (dY(t.y1) + dY(t.y2)) / 2 : (p.view?.y ?? dY(p.obj.y1));
    centerOn(fx, fy, null); // re-derives the focus zoom for this viewport
    flashAt(fx, fy, true);
    toast(t ? `marker on ${t.name}` : `no ${p.obj.name} at that spot`);
  }
  state.route = p.route; // the hash is the source of truth: absent means no route
  if (p.routeLost)
    toast(`route link cut short: ${p.route.length} of ${p.route.length + p.routeLost} waypoints`);
  window.dispatchEvent(new CustomEvent("route-changed"));
  draw();
  return true;
}

window.addEventListener("hashchange", () => {
  if (applyingHash) return;
  // back/forward retraces update the remembered spot; a rejected hash must not
  if (applyHash() && !inEmbed()) rememberLocation(location.hash);
});
