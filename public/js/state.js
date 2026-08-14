// Shared mutable viewer state and the world-to-draw coordinate transforms.

import { GRID_UNIT } from "./config.js";

// Both games address cameras on a grid coarser than the screen (data.geometry):
// a visW x visH window of world units sits inside the cell at winX/winY, world
// units being PS1 screen pixels and the artwork 1:1 with them. AO's cell is
// 1024x480 with a 368x240 window at +256/+120; AE's is 375x260 with the same
// window at +0/+0. Draw space is world units too, so a screen's interior maps
// 1:1 and cellW/cellH are only the pitch screens are laid out at: packed edge
// to edge, which folds away the slack between windows.
export let GEO = null,
  CELL_W = 368,
  CELL_H = 240;

export function setGeometry(g) {
  GEO = g;
  CELL_W = g.cellW;
  CELL_H = g.cellH;
}

export function dX(wx) {
  const c = Math.floor(wx / GEO.worldW);
  return c * CELL_W + (wx - c * GEO.worldW - GEO.winX);
}
export function dY(wy) {
  const c = Math.floor(wy / GEO.worldH);
  return c * CELL_H + (wy - c * GEO.worldH - GEO.winY);
}
export function wX(dx) {
  const c = Math.floor(dx / CELL_W);
  return c * GEO.worldW + GEO.winX + (dx - c * CELL_W);
}
export function wY(dy) {
  const c = Math.floor(dy / CELL_H);
  return c * GEO.worldH + GEO.winY + (dy - c * CELL_H);
}

// position within its own screen, in grid squares (measured from the visible
// window's corner, so both games read 0 at a screen's left/top edge)
export const gX = (wx) => (wx - Math.floor(wx / GEO.worldW) * GEO.worldW - GEO.winX) / GRID_UNIT;
export const gY = (wy) => (wy - Math.floor(wy / GEO.worldH) * GEO.worldH - GEO.winY) / GRID_UNIT;

// world-unit length of a draw-space delta: a screen's interior is 1:1, so the
// delta is already a world length; the folded-away slack stays uncounted
export const worldLen = (dx, dy) => Math.hypot(dx, dy);

// total world-unit length over [{x, y}, …] draw-space waypoints
export const routeTotal = (pts) =>
  pts.reduce((sum, p, i) => (i ? sum + worldLen(p.x - pts[i - 1].x, p.y - pts[i - 1].y) : 0), 0);

export const state = {
  games: [], // one dataset per available game
  data: null, // current game's dataset
  lvl: null, // current level
  path: null, // current path
  entry: {}, // per game: level short -> Set of path ids arrived into from other levels
  cam: { x: 0, y: 0, z: 0.3 }, // view offset + zoom (px per draw unit)
  show: {}, // display toggles, mirrored from the sidebar checkboxes
  ruler: null, // {x1, y1, x2, y2} in draw space
  route: null, // route segments [{lv, pa, pts: [{x, y}, …]}, …], pts in draw space; drawn whenever set (show.route only gates editing)
};
