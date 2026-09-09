import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CAM_FILE_BYTES } from "../../public/js/config.js";
import { camFiles } from "../../public/js/model.js";

const read = (name) => readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8");
const load = (name) => JSON.parse(read(name));

const GAMES = [
  ["map_data_ao.json", 935],
  ["map_data_ae.json", 1953],
];

for (const [file, files] of GAMES)
  test(`${file}: camFiles lists every artwork file once`, () => {
    const list = camFiles(load(file));
    assert.equal(list.length, files);
    assert.equal(new Set(list).size, list.length, "no file is listed twice");
    assert.ok(
      list.every((f) => /^cams\/[a-z]{2}\/[^/]+\/[^/]+\.png$/.test(f)),
      "every entry is a cam png path",
    );
    // the foreground layers are half the download and easy to leave out
    assert.ok(list.some((f) => f.endsWith("_fg.png")));
  });

// the download stores a whole game at once, so a cap below the complete set
// would silently evict the head of what it just fetched
test("both games' artwork fits the worker's cache cap", () => {
  const cap = Number(/^const MAX_ENTRIES = (\d+);/m.exec(read("sw.js"))[1]);
  const total = GAMES.reduce((n, [file]) => n + camFiles(load(file)).length, 0);
  assert.ok(total <= cap, `${total} files vs a ${cap}-entry cap`);
});

// the figures are hand-written where they are quoted, so a rebuild that adds
// artwork has to move them
test("the cap comment, the README and the changelog quote the artwork as it ships", () => {
  const files = GAMES.map(([file]) => camFiles(load(file)).length);
  const total = files.reduce((n, f) => n + f, 0);
  assert.equal(Number(/complete artwork \((\d+) files\)/.exec(read("sw.js"))[1]), total);
  const mb = files.map((f) => Math.round((f * CAM_FILE_BYTES) / 1e6));
  const readme = readFileSync(new URL("../../README.md", import.meta.url), "utf8");
  for (const [text, quote] of [
    [readme, /~(\d+) MB for Oddysee, ~(\d+) MB for Exoddus/],
    [read("changelog.json"), /about (\d+) MB for Oddysee, (\d+) MB for Exoddus/],
  ])
    assert.deepEqual(quote.exec(text).slice(1).map(Number), mb);
});
