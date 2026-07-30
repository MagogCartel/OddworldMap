// "About this map": what the project is, whose trademarks it uses, and where
// its source lives. Wires itself up at import time; the prose is static markup
// so the notice is in the page source with scripting off.

import { $ } from "./dom.js";
import { trapDialogKeys } from "./dialog.js";

const btn = $("aboutBtn"),
  overlay = $("aboutOverlay"),
  closeBtn = $("aboutClose");

const open = () => {
  document.body.classList.add("about-open");
  closeBtn.focus();
};
const close = () => {
  document.body.classList.remove("about-open");
  btn.focus();
};

btn.onclick = open;
closeBtn.onclick = close;
overlay.onclick = (e) => {
  if (e.target === overlay) close();
};
trapDialogKeys(() => document.body.classList.contains("about-open"), $("about"), close);
