// Where the map is: a chip in the map chrome naming the current level and path,
// and the panel it discloses — the level's full name, which half of it the path
// belongs to, the nickname players gave it where the map has adopted one,
// whether the path is arrived at from another level or one the demos alone play,
// and the curated note the odd places carry.

import { $ } from "./dom.js";
import { esc } from "./util.js";
import { state } from "./state.js";
import { pathDisplayName, pathNickname, pathNote } from "./annotations.js";
import { isDemoPath } from "./demo.js";

const btn = $("placeBtn"),
  panel = $("placePanel"),
  codeEl = $("placeCode"),
  nameEl = $("placeName");

let shown = null; // the path the open panel describes

function fill() {
  const { data, lvl, path } = state;
  const name = pathDisplayName(data.id, lvl.short, path),
    note = pathNote(data.id, lvl.short, path),
    nickname = pathNickname(data.id, lvl.short, path);
  panel.innerHTML =
    `<div class="pl-game">${esc(data.game)}</div>` +
    `<div class="pl-level">${esc(lvl.name)}</div>` +
    (path.section ? `<div class="pl-section">${esc(path.section)}</div>` : "") +
    `<div>Path ${path.id}${name ? ` — ${esc(name)}` : ""}</div>` +
    (nickname ? `<div class="pl-nickname">${esc(nickname)}</div>` : "") +
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
  if (open) {
    panel.hidden = false;
    syncPlace();
    // the prose is what the chip was pressed for, and nothing announces it
    if (panel.offsetParent) panel.focus();
    return;
  }
  const held = panel.contains(document.activeElement);
  panel.hidden = true;
  shown = null;
  if (held) btn.focus();
}

export function togglePlace(open) {
  if (!state.path) return;
  setOpen(open ?? panel.hidden);
}

// a re-selection of the path the panel already describes must not rebuild it:
// the pushed hash rewrite re-fires selection-changed on the same path constantly,
// and a rebuild would throw away the reader's scroll position
function syncPlace() {
  if (!panel.hidden && state.path && state.path !== shown) fill();
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
