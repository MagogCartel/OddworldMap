// The map's own places as search targets: a level, or one path within it.
// No DOM, so it stays importable in bare Node.

import { pathDisplayName, pathNickname } from "./annotations.js";
import { matchesBy, rankFor } from "./searchquery.js";

// names go into a substring blob the way an object's fields do; the LV/Pn code
// is held as whole tokens, so the "2" in "zulag 2" is not answered by an "R2"
function gameCandidates(G) {
  const out = [];
  for (const L of G.levels) {
    out.push({
      G,
      L,
      P: null,
      code: L.short,
      name: L.name || null,
      text: (L.name || "").toLowerCase(),
      tokens: [L.short.toLowerCase()],
    });
    for (const P of L.paths) {
      const name = pathDisplayName(G.id, L.short, P),
        nickname = pathNickname(G.id, L.short, P),
        section = P.section || null;
      out.push({
        G,
        L,
        P,
        code: `${L.short} P${P.id}`,
        name,
        nickname,
        section,
        text: [L.name, name, nickname, section].filter(Boolean).join(" ").toLowerCase(),
        tokens: [L.short.toLowerCase(), "p" + P.id],
      });
    }
  }
  return out;
}

// data and annotations are fixed after boot, so the key needs no invalidation
const candidateCache = new WeakMap();

export function placeCandidates(games) {
  return games.flatMap((G) => {
    let rows = candidateCache.get(G);
    if (!rows) candidateCache.set(G, (rows = gameCandidates(G)));
    return rows;
  });
}

// a path is indexed on its level's name but never ranks on it: that is what the
// level's own row answers, so a level sorts above the paths inside it
const rankPlace = (c, terms) =>
  Math.min(
    ...[c.name, c.nickname, c.section, c.code].filter(Boolean).map((s) => rankFor(s, terms)),
  );

// scope and the demo-path setting are the caller's, as they are for objects
export function matchPlaces(games, groups, terms, current) {
  return placeCandidates(games)
    .filter((c) => matchesBy(groups, (term) => c.text.includes(term) || c.tokens.includes(term)))
    .map((c) => ({ ...c, rank: rankPlace(c, terms) }))
    .sort((a, b) => a.rank - b.rank || (b.G === current) - (a.G === current));
}
