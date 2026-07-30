// The definition behind a .gloss field name: hover it with a mouse, tap it on
// touch. Delegated from the document, so the surfaces that carry one can
// rebuild their DOM freely and a new one is a class away.

import { $ } from "./dom.js";
import { clamp } from "./util.js";

const el = $("glossTip");
let anchor = null;

const glossAt = (e) => e.target.closest?.(".gloss");

// first line is the definition, the rest its value list
function show(target) {
  const text = target.dataset.tip;
  if (!text) return;
  const [def, ...rest] = text.split("\n");
  el.textContent = "";
  const defEl = document.createElement("div");
  defEl.textContent = def;
  el.append(defEl);
  if (rest.length) {
    const vals = document.createElement("div");
    vals.className = "gt-vals";
    vals.textContent = rest.join("\n");
    el.append(vals);
  }
  anchor = target;
  el.hidden = false;
  place();
}

function place() {
  const r = anchor.getBoundingClientRect();
  el.style.left = "0px"; // the width it wraps to given the whole viewport to grow into
  const w = el.offsetWidth,
    h = el.offsetHeight;
  const vw = document.documentElement.clientWidth,
    vh = document.documentElement.clientHeight;
  const below = r.bottom + 6;
  el.style.left = clamp(r.left, 6, vw - w - 6) + "px";
  el.style.top = (below + h <= vh - 6 ? below : Math.max(6, r.top - h - 6)) + "px";
}

function hide() {
  if (!anchor) return;
  el.hidden = true;
  anchor = null;
}

// a touch fires pointerover before its own tap and pointerout after it, so
// hover has to be the mouse's alone or a tap would flash the definition away
document.addEventListener("pointerover", (e) => {
  if (e.pointerType !== "mouse") return;
  const g = glossAt(e);
  if (g) show(g);
});
document.addEventListener("pointerout", (e) => {
  if (e.pointerType === "mouse" && glossAt(e) === anchor) hide();
});
// the tap coexists with what it activates: nothing is consumed here, so
// whatever the span sits inside still gets the click
document.addEventListener("pointerup", (e) => {
  if (e.pointerType === "mouse") return;
  const g = glossAt(e);
  if (g) show(g);
});
document.addEventListener("pointerdown", (e) => {
  if (!glossAt(e)) hide();
});
document.addEventListener("scroll", hide, true); // scroll doesn't bubble: only capture sees a host scroll
window.addEventListener("resize", hide);
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") hide();
});
