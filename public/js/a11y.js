// The map's spoken half: a status region saying where the selection has landed,
// and the same sentence in the canvas's own name, so a screen reader meets a
// named picture rather than an anonymous graphic.

import { $, cv } from "./dom.js";
import { state } from "./state.js";
import { placeSummary } from "./placesummary.js";

const region = $("a11yStatus");

const SETTLE_MS = 250; // how long the region waits for a run of steps to stop

let announced = null,
  timer = null;

window.addEventListener("selection-changed", () => {
  const { data, lvl, path } = state;
  if (!path || path === announced) return;
  announced = path;
  const summary = placeSummary(data, lvl, path);
  // a name is not a live region, so this speaks nothing of its own
  cv.setAttribute("aria-label", `Oddworld map: ${summary}`);
  clearTimeout(timer);
  timer = setTimeout(() => (region.textContent = summary), SETTLE_MS);
});
