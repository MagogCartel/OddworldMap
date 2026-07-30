// "About this map": what the project is, whose trademarks it uses, and where
// its source lives. Wires itself up at import time; the prose is static markup
// so the notice is in the page source with scripting off.

import { $ } from "./dom.js";
import { trapDialogKeys } from "./dialog.js";

const btn = $("aboutBtn"),
  overlay = $("aboutOverlay"),
  closeBtn = $("aboutClose");

const open = () => {
  overlay.classList.add("open");
  closeBtn.focus();
};
const close = () => {
  overlay.classList.remove("open");
  btn.focus();
};

btn.onclick = open;
closeBtn.onclick = close;
overlay.onclick = (e) => {
  if (e.target === overlay) close();
};
trapDialogKeys(() => overlay.classList.contains("open"), $("about"), close);
