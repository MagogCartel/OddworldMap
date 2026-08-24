// Per-camera object list: clicking a screen with nothing to follow under the
// pointer lists everything on it. Hover doesn't exist on touch devices, so
// this panel is also the mobile way to inspect a screen's objects, and `l`
// the keyboard's only way.

import { esc } from "./util.js";
import { fieldEntries, fieldHelp } from "./fields.js";
import { CATS, OFFSCREEN_NOTE, catOf } from "./config.js";
import { $, narrowMQ } from "./dom.js";
import { state } from "./state.js";
import { cellAt, markerCentre, nearestCam, offScreen } from "./model.js";
import { setHighlight } from "./render.js";
import { fieldPrefsFor, getSettings } from "./settings.js";
import { jumpToTlv } from "./navigate.js";

const panel = $("camPanel"),
  title = $("camPanelTitle"),
  body = $("camPanelBody");

let listedPath = null; // the path the open panel was built from
let lastOpen = null; // args of the current open, so a settings change can rebuild it
let opener = null; // where focus returns when a panel holding it closes

function closeCamPanel() {
  // read before the hide: hiding a subtree holding the focus drops it to <body>
  const held = panel.contains(document.activeElement);
  panel.hidden = true;
  listedPath = null;
  lastOpen = null;
  setHighlight(null);
  // the opener may be gone or hidden by now (its surface re-rendered or closed)
  if (held && opener?.isConnected && opener.offsetParent) opener.focus();
  opener = null;
}

// the panel is named by its own title, so focus landing on it says which screen
// and how much is on it before the rows do
export function focusCamPanel() {
  if (!panel.contains(document.activeElement)) opener = document.activeElement;
  panel.focus();
}

// (x, y) in draw space: list the camera cell under it, all categories —
// the panel is an inventory of the screen, not a view of the filters.
// A focus object gets its row marked and scrolled into view, so tapping an
// object reads as inspecting it (touch has no hover tooltip)
export function openCamPanel(x, y, focus = null) {
  const { path } = state;
  if (!path) return;
  const cell = cellAt(x, y, path);
  const cam = cell != null && path.cams.find((c) => c.cell === cell);
  if (!cam) {
    closeCamPanel(); // clicked the void between/outside screens: dismiss
    return;
  }
  opener = null; // a pointer brought no focus with it
  list(cam, focus);
}

// the keyboard aims with the one point it has, the view's centre
export function openCamPanelNear(x, y) {
  const { path } = state;
  if (!path) return false;
  const cam = nearestCam(x, y, path);
  if (!cam) return false;
  list(cam, null);
  return true;
}

function list(cam, focus) {
  const { path } = state,
    cell = cam.cell;
  // objects bucket by rect centre in draw space — an inventory rule; the
  // resolution logic (tlvCell) buckets by world top-left, which can differ
  // for an edge-straddling object
  const inCell = (t) => cellAt(...markerCentre(t), path) === cell;
  const byCat = new Map(CATS.map((c) => [c, []]));
  let n = 0;
  for (const t of path.tlvs)
    if (inCell(t)) {
      byCat.get(catOf(t)).push(t);
      n++;
    }

  title.innerHTML = `${esc(cam.name)} <span class="e">· ${n} object${n === 1 ? "" : "s"}</span>`;
  body.innerHTML = "";
  for (const [c, tlvs] of byCat) {
    if (!tlvs.length) continue;
    const head = document.createElement("div");
    head.className = "listhead cp-cat";
    head.innerHTML = `<span class="sw" style="background:${c.color}"></span>${c.label}`;
    body.appendChild(head);
    for (const t of tlvs) {
      const b = document.createElement("button");
      b.className = "rowbtn cp-row";
      if (t === focus) b.classList.add("active");
      const ex = fieldEntries(t, fieldPrefsFor(state.data.id))
        .map(([k, v]) => {
          const help = fieldHelp(state.data.id, t.name, k);
          const kv = esc(`${k}=${v}`);
          return help
            ? `<span class="e gloss" data-tip="${esc(help)}">${kv}</span>`
            : `<span class="e">${kv}</span>`;
        })
        .join(" ");
      // the list buckets by where a marker is drawn, so one anchored between
      // windows is listed under the screen it was folded onto, not its own
      const off = offScreen(t)
        ? ` <span class="e gloss" data-tip="${esc(OFFSCREEN_NOTE)}">· offscreen</span>`
        : "";
      b.innerHTML = esc(t.name) + off + (ex ? " " + ex : "");
      b.onclick = () => jumpToTlv(state.data, state.lvl, state.path, t);
      b.onmouseenter = () => setHighlight(t);
      b.onmouseleave = () => setHighlight(null);
      const wrap = document.createElement("div");
      wrap.className = "cp-row-wrap";
      wrap.append(b);
      // with the field picker on, a ⚙ jumps to this type's row in it
      if (t.fields && getSettings().fieldPrefs.mode === "more") {
        const gear = document.createElement("button");
        gear.className = "rowtool";
        gear.type = "button";
        gear.textContent = "⚙";
        gear.title = `Configure ${t.name} fields`;
        gear.setAttribute("aria-label", gear.title);
        gear.onclick = () =>
          window.dispatchEvent(new CustomEvent("reveal-field-type", { detail: { type: t.name } }));
        wrap.append(gear);
      }
      const info = document.createElement("button");
      info.className = "rowtool";
      info.type = "button";
      info.textContent = "ⓘ";
      info.title = `About ${t.name}`;
      info.setAttribute("aria-label", info.title);
      info.onclick = () =>
        window.dispatchEvent(new CustomEvent("typecard-open", { detail: { type: t.name } }));
      wrap.append(info);
      body.appendChild(wrap);
    }
  }
  if (!n) body.innerHTML = `<div class="cp-none">no objects on this screen</div>`;
  listedPath = path;
  lastOpen = { cam, focus };
  panel.hidden = false;
  window.dispatchEvent(new CustomEvent("float-opened", { detail: { id: "camPanel" } }));
  body.querySelector(".active")?.scrollIntoView({ block: "nearest" }); // after unhide: needs layout
}

// narrow screens hold one floating panel at a time — two bottom sheets stack
window.addEventListener("float-opened", (e) => {
  if (narrowMQ.matches && e.detail.id !== "camPanel" && !panel.hidden) closeCamPanel();
});

// the world graph stands over the map this describes, and it is unusable and
// out of date by the time the mode closes
window.addEventListener("graph-changed", () => {
  if (state.graph) closeCamPanel();
});

$("camPanelClose").onclick = closeCamPanel;
// close when the listed path is gone; same-path re-selections (every pushed
// hash write re-applies the hash) keep the panel, so a row jump doesn't
// yank the list away mid-browse
window.addEventListener("selection-changed", () => {
  if (!panel.hidden && state.path !== listedPath) closeCamPanel();
});

// field-display settings change how the listed objects render — raw vs
// prettified values, the ⚙ affordance (mode), and which fields show (per-type
// picks); rebuild the open panel so it doesn't sit stale
window.addEventListener("settings-changed", (e) => {
  const key = e.detail?.key;
  if (
    (key === "rawValues" || key === "fieldPrefs" || key === "fieldPicks") &&
    !panel.hidden &&
    lastOpen
  )
    list(lastOpen.cam, lastOpen.focus);
});

window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !panel.hidden && !e.target.matches?.("input, textarea, select"))
    closeCamPanel();
});
