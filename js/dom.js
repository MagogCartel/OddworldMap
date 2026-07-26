// Cached references to the static DOM and browser-environment handles.

import { TOAST_MS } from "./config.js";

export const $ = (id) => document.getElementById(id);

export const narrowMQ = window.matchMedia("(max-width: 720px)"); // keep in sync with the CSS breakpoint

// one-off reads of stylesheet tokens
export const cssVar = (name) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export const cv = $("cv"),
  ctx = cv.getContext("2d");
export const tip = $("tip"),
  hud = $("hud");
export const menuBtn = $("menuBtn"),
  scrim = $("scrim"),
  copyLinkBtn = $("copyLinkBtn"),
  openSiteBtn = $("openSiteBtn");
export const gameBtns = $("gameBtns"),
  levelBtns = $("levelBtns"),
  pathBtns = $("pathBtns");
export const filterBox = $("filterBox");
export const searchInput = $("searchInput"),
  searchResults = $("searchResults"),
  scopeBar = $("scopeBar");
// transient notice at the bottom of the map; it lives with the DOM handles so
// that any module can raise one without closing an import cycle
const toastEl = $("toast");
let toastTimer = null;
export function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("show"), TOAST_MS);
}
