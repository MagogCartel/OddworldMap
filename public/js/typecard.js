// The type encyclopedia card: what an object type is, in one dialog — the
// curated paragraph (glossary_types.json), its category, live per-game placement
// counts, and the type's curated field meanings — with a button that seeds
// search with the type name. Any surface opens it by dispatching the
// "typecard-open" window event, so none has to import this module.

import { $, narrowMQ, searchInput } from "./dom.js";
import { esc } from "./util.js";
import { state } from "./state.js";
import { catOf } from "./config.js";
import { census } from "./census.js";
import { fieldHelp } from "./fields.js";
import { typeProse } from "./typeinfo.js";
import { closeDialog, openDialog, trapDialogKeys } from "./dialog.js";
import { toggleMenu } from "./interaction.js";

const overlay = $("typeCardOverlay"),
  panel = $("typeCard"),
  title = $("typeCardTitle"),
  body = $("typeCardBody"),
  closeBtn = $("typeCardClose");

const GAME_SHORT = { AO: "Oddysee", AE: "Exoddus" };

let opener = null; // where focus returns on close

// a game's union of field names for a type, from the data itself
const fieldsCache = new WeakMap(); // dataset -> Map(type -> Set(field))
function fieldKeys(G, name) {
  let m = fieldsCache.get(G);
  if (!m) {
    m = new Map();
    for (const L of G.levels)
      for (const P of L.paths)
        for (const t of P.tlvs) {
          if (!t.fields) continue;
          let s = m.get(t.name);
          if (!s) m.set(t.name, (s = new Set()));
          for (const k of Object.keys(t.fields)) s.add(k);
        }
    fieldsCache.set(G, m);
  }
  return [...(m.get(name) ?? [])].sort((a, b) => a.localeCompare(b));
}

function render(name) {
  title.textContent = name;
  body.innerHTML = "";

  const cat = catOf({ name });
  const catLine = document.createElement("div");
  catLine.className = "tc-cat";
  catLine.innerHTML = `<span class="sw" style="background:${cat.color}"></span>${esc(cat.label)}`;
  body.append(catLine);

  const prose = typeProse(name);
  if (prose) {
    const p = document.createElement("p");
    p.className = "tc-prose";
    p.textContent = prose;
    body.append(p);
  }

  // placement counts, derived live: what the map lists per game, and what the
  // demo setting is keeping off it
  const parts = [];
  let demoNote = "";
  for (const G of state.games) {
    const { rows, demo } = census([name], G, state.lvl, state.path, null);
    const n = rows[0].game;
    if (n || demo) parts.push(`${n} in ${GAME_SHORT[G.id] ?? G.id}`);
    if (demo) demoNote = `demo paths hold ${demo} more (hidden by the demo setting)`;
  }
  const counts = document.createElement("div");
  counts.className = "tc-counts";
  counts.textContent = parts.join(" · ");
  if (demoNote) {
    const d = document.createElement("div");
    d.className = "e";
    d.textContent = demoNote;
    counts.append(d);
  }
  body.append(counts);

  // the fields the glossary has meanings for, in the current game's terms
  const defs = [];
  for (const k of fieldKeys(state.data, name)) {
    const help = fieldHelp(state.data.id, name, k);
    if (help) defs.push([k, help]);
  }
  if (defs.length) {
    const head = document.createElement("div");
    head.className = "listhead tc-fhead";
    head.textContent = "Fields";
    body.append(head);
    for (const [k, help] of defs) {
      const [def, ...rest] = help.split("\n");
      const row = document.createElement("div");
      row.className = "tc-field";
      row.innerHTML =
        `<span class="tc-fname">${esc(k)}</span> — ${esc(def)}` +
        (rest.length ? ` <span class="e">${esc(rest.join(" "))}</span>` : "");
      body.append(row);
    }
  }

  const find = document.createElement("button");
  find.type = "button";
  find.className = "linkbtn tc-find";
  find.textContent = `find every ${name} with search`;
  find.onclick = () => {
    close();
    toggleMenu(true);
    searchInput.value = name;
    searchInput.dispatchEvent(new Event("input"));
    // focusing would pop the keyboard over the results on touch screens
    if (!narrowMQ.matches) searchInput.focus();
  };
  body.append(find);
}

function open(name) {
  if (!state.data) return;
  opener = document.activeElement;
  render(name);
  openDialog(overlay, close);
  body.scrollTop = 0;
  closeBtn.focus();
}

function close() {
  closeDialog(overlay);
  // the opener may be gone or hidden by now (its surface re-rendered or closed)
  if (opener?.isConnected && opener.offsetParent) opener.focus();
  opener = null;
}

window.addEventListener("typecard-open", (e) => open(e.detail.type));
closeBtn.onclick = close;
overlay.onclick = (e) => {
  if (e.target === overlay) close();
};
trapDialogKeys(() => overlay.classList.contains("open"), panel, close);
