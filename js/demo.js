// Exoddus keeps copies of areas that only its title-screen demos ever play;
// they are unreachable however you play, so the map lists them only when asked.
// A path is one of them exactly when it holds a DemoSpawnPoint. Importable in
// bare Node: no DOM.

import { getSettings } from "./settings.js";

// path objects live as long as their dataset, so identity keys need no invalidation
const demo = new WeakMap();
const revealed = new WeakSet();

export function isDemoPath(P) {
  let d = demo.get(P);
  if (d === undefined) demo.set(P, (d = P.tlvs.some((t) => t.name === "DemoSpawnPoint")));
  return d;
}

// a label says which class the path is in, because the chip and the buttons have
// no room for the sentence the place panel gets
export function demoLabel(P, name) {
  return isDemoPath(P) ? `[Demo] ${name || ""}`.trimEnd() : name;
}

// the path in hand is always listed: a hidden path arrived at is revealed for the
// session rather than stranding the visitor on a screen no button names
export function pathVisible(P) {
  return !isDemoPath(P) || getSettings().showDemoPaths || revealed.has(P);
}

// true when this reveals the path, so the caller knows to rebuild its buttons
export function revealPath(P) {
  if (pathVisible(P)) return false;
  revealed.add(P);
  return true;
}
