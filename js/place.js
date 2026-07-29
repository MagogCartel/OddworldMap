// Where the map is: a chip in the map chrome naming the current level and path,
// and the panel it discloses — the level's full name, which half of it the path
// belongs to, whether the path is arrived at from another level or one the demos
// alone play, and the curated note the odd places carry.

import { $ } from "./dom.js";
import { esc } from "./util.js";
import { state } from "./state.js";
import { pathDisplayName, pathNote } from "./annotations.js";
import { isDemoPath } from "./demo.js";

const btn = $("placeBtn"),
  panel = $("placePanel"),
  codeEl = $("placeCode"),
  nameEl = $("placeName");

let shown = null; // the path the open panel describes; a re-selection must not re-announce

// the panel is a live region, and a live region announces only what is written
// into it while it is visible — so every fill follows the unhide
function fill() {
  const { data, lvl, path } = state;
  const name = pathDisplayName(data.id, lvl.short, path),
    note = pathNote(data.id, lvl.short, path);
  panel.innerHTML =
    `<div class="pl-game">${esc(data.game)}</div>` +
    `<div class="pl-level">${esc(lvl.name)}</div>` +
    (path.section ? `<div class="pl-section">${esc(path.section)}</div>` : "") +
    `<div>Path ${path.id}${name ? ` — ${esc(name)}` : ""}</div>` +
    (state.entry[lvl.short]?.has(path.id)
      ? `<div class="pl-entry">entry point — arrived at from another level</div>`
      : "") +
    (isDemoPath(path)
      ? `<div class="pl-demo">demo path — the game only plays this in its title-screen demos</div>`
      : "") +
    (note ? `<div class="pl-note">${esc(note)}</div>` : "");
  shown = path;
}

function setOpen(open) {
  btn.setAttribute("aria-expanded", String(open));
  panel.hidden = !open;
  if (open) syncPlace();
  else shown = null;
}

export function togglePlace(open) {
  if (!state.path) return;
  setOpen(open ?? panel.hidden);
}

// an open panel can be covered rather than closed — on narrow the drawer takes
// the screen while the panel keeps its state — and a write made under the cover
// is a write nothing announces, so it waits here until the cover lifts
export function syncPlace() {
  if (!panel.hidden && panel.offsetParent && state.path && state.path !== shown) fill();
}

btn.onclick = () => togglePlace();

window.addEventListener("selection-changed", () => {
  const { data, lvl, path } = state;
  if (!path) {
    btn.hidden = true;
    setOpen(false);
    return;
  }
  codeEl.textContent = `${lvl.short} P${path.id}`;
  nameEl.textContent = pathDisplayName(data.id, lvl.short, path) || "";
  btn.classList.toggle("hasnote", !!pathNote(data.id, lvl.short, path));
  btn.hidden = false;
  syncPlace();
});

window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !panel.hidden && !e.target.matches?.("input, textarea, select"))
    togglePlace(false);
});
