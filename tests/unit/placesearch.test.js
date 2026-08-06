import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { placeCandidates, matchPlaces } from "../../public/js/placesearch.js";
import { parseQuery, queryTerms } from "../../public/js/searchquery.js";
import { setAnnotations } from "../../public/js/annotations.js";

const load = (name) =>
  JSON.parse(readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8"));

const run = (games, q, current = games[0]) => {
  const groups = parseQuery(q);
  return matchPlaces(games, groups, queryTerms(groups), current);
};
const where = (hits) => hits.map((c) => `${c.G.id} ${c.code}`);

// two stand-in games carrying one of each thing the blob is built from: a disc
// name, a curated name, a nickname, a section — and a level short ending in the
// digit a query is about to ask for
const GAMES = [
  {
    id: "XX",
    levels: [
      { short: "L1", name: "Monsaic Lines", paths: [{ id: 1 }, { id: 3 }] },
      {
        short: "R2",
        name: "Rupture Farms Return",
        paths: [{ id: 1, name: "Zulag 2" }, { id: 4, section: "Ender Wing" }, { id: 12 }],
      },
    ],
  },
  {
    id: "YY",
    levels: [{ short: "BR", name: "SoulStorm Brewery", paths: [{ id: 2 }] }],
  },
];
const ANN = {
  XX: { paths: { L1: { 3: "The Chant Gate" } } },
  YY: { paths: { BR: { 2: { name: "Zulag 2", nickname: "Flying Sligs" } } } },
};

test("placeCandidates: one row per level and per path", () => {
  setAnnotations(ANN);
  const cands = placeCandidates(GAMES);
  assert.equal(cands.length, 3 + 6); // 3 levels, 6 paths

  const level = cands.find((c) => c.code === "L1");
  assert.equal(level.P, null);
  assert.equal(level.name, "Monsaic Lines");
  assert.equal(level.text, "monsaic lines");
  assert.deepEqual(level.tokens, ["l1"]);

  // a path indexes its level's name alongside its own, so a level name finds
  // what is inside it
  const path = cands.find((c) => c.code === "L1 P3");
  assert.equal(path.name, "The Chant Gate");
  assert.equal(path.text, "monsaic lines the chant gate");
  assert.deepEqual(path.tokens, ["l1", "p3"]);

  const unnamed = cands.find((c) => c.code === "L1 P1");
  assert.equal(unnamed.name, null);
  assert.equal(unnamed.text, "monsaic lines");
});

test("matchPlaces: a level's name reaches its paths, and the level still leads", () => {
  setAnnotations(ANN);
  assert.deepEqual(where(run(GAMES, "monsaic")), ["XX L1", "XX L1 P1", "XX L1 P3"]);
});

test("matchPlaces: the code answers a whole term only", () => {
  setAnnotations(ANN);
  // "R2 P12" holds both a 2 and a 1, so a plain blob would answer either query
  assert.deepEqual(where(run(GAMES, "zulag 2")), ["XX R2 P1", "YY BR P2"]);
  assert.deepEqual(where(run(GAMES, "r2 p12")), ["XX R2 P12"]);
  assert.deepEqual(where(run(GAMES, "l1 p3, br p2")), ["XX L1 P3", "YY BR P2"]);
});

test("matchPlaces: a nickname and a section are as findable as a name", () => {
  setAnnotations(ANN);
  assert.deepEqual(where(run(GAMES, "flying sligs")), ["YY BR P2"]);
  assert.deepEqual(where(run(GAMES, "ender")), ["XX R2 P4"]);
});

test("matchPlaces: the current game breaks a rank tie", () => {
  setAnnotations(ANN);
  assert.deepEqual(where(run(GAMES, "zulag 2", GAMES[1])), ["YY BR P2", "XX R2 P1"]);
});

test("matchPlaces: the queries the sidebar's buttons were the only answer to", () => {
  setAnnotations(load("annotations.json"));
  const games = [load("map_data_ao.json"), load("map_data_ae.json")];
  const hits = (q) => where(run(games, q));

  // a level name leads the paths it reaches
  assert.equal(hits("monsaic")[0], "AO L1");
  assert.equal(hits("feeco")[0], "AE FD");
  assert.deepEqual(
    hits("necrum").filter((h) => !h.includes("P")),
    ["AE NE", "AE MI"],
  );

  // the four Rupture Farms Return paths the game itself calls Zulag 2 lead, and
  // not the fourteen others whose R2 would answer a "2" in a plain blob; the
  // names stay a substring index, so AE's Zulag 12 follows on its "12"
  assert.deepEqual(hits("zulag 2").slice(0, 4), ["AO R2 P1", "AO R2 P2", "AO R2 P3", "AO R2 P10"]);

  assert.deepEqual(hits("r2 p1"), ["AO R2 P1"]);
  assert.ok(run(games, "p3").every((c) => c.P?.id === 3));

  // the nicknames, which are the half of this a player reaches for when they
  // know what a place is like but not what it is called
  assert.deepEqual(hits("tear extractors"), ["AE BR P11"]);
  assert.deepEqual(hits("high security"), ["AE BR P10"]);
});
