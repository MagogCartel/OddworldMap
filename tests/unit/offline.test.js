import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { camFiles } from "../../public/js/model.js";

const read = (name) => readFileSync(new URL(`../../public/${name}`, import.meta.url), "utf8");
const load = (name) => JSON.parse(read(name));

const GAMES = [
  ["map_data_ao.json", 935],
  ["map_data_ae.json", 1936],
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
