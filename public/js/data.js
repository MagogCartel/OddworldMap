// The site's JSON payloads and when each is fetched: first paint waits on the
// game the link names, and the other arrives behind it.
// No DOM, so it stays importable in bare Node.

import { parseHash } from "./model.js";

// the games in canonical order; the first is what a visit boots on when
// nothing names one
export const GAME_FILES = { AO: "map_data_ao.json", AE: "map_data_ae.json" };
export const GAME_IDS = Object.keys(GAME_FILES);
export const knownGame = (id) => Object.hasOwn(GAME_FILES, id);

export async function loadJson(file, init) {
  try {
    // no-cache revalidates (ETag/304) so rebuilds still show up immediately,
    // but an unchanged file is not re-downloaded
    const r = await fetch(file, { cache: "no-cache", ...init });
    if (r.ok) return await r.json();
  } catch {
    /* tolerate a missing file */
  }
  return null;
}

// read from the hash text alone: a parse costs nothing, and the answer is needed
// before there is any geometry to resolve the rest of the link against
export function bootGame(hash, stored) {
  for (const h of [hash, stored]) {
    const id = h ? parseHash(h)?.game : null;
    if (id && knownGame(id)) return id;
  }
  return GAME_IDS[0];
}

const started = new Map(),
  settled = new Set();

// one fetch per dataset however many callers ask, so a permalink into a game
// still in flight awaits that fetch rather than starting a second. `low` drops
// the game the visitor is not looking at out of the default high priority, so it
// cannot push ahead of the opening screen's artwork, which is low itself.
export function loadGame(id, low) {
  let p = started.get(id);
  if (!p)
    started.set(
      id,
      (p = loadJson(GAME_FILES[id], low ? { priority: "low" } : null)
        .then((d) => (d && d.levels && d.levels.length ? d : null))
        .finally(() => settled.add(id))),
    );
  return p;
}

// the games that have neither landed nor been given up on
export const pendingGames = () => GAME_IDS.filter((id) => !settled.has(id));
