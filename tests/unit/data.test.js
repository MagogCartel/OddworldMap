import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { GAME_FILES, GAME_IDS, bootGame, knownGame } from "../../public/js/data.js";

test("knownGame: the games the map ships, and nothing borrowed from Object", () => {
  for (const id of GAME_IDS) assert.equal(knownGame(id), true);
  assert.equal(knownGame("XX"), false);
  assert.equal(knownGame("constructor"), false);
});

test("bootGame: the link's game, else the remembered one, else the first", () => {
  assert.equal(bootGame("#AE/MI/1", null), "AE");
  assert.equal(bootGame("#ao/R1/1", null), "AO"); // parseHash uppercases
  assert.equal(bootGame("", "#AE/MI/1"), "AE");
  assert.equal(bootGame(null, null), GAME_IDS[0]);
  // a link the map cannot answer must not decide which dataset boots
  assert.equal(bootGame("#XX/R1/1", "#AE/MI/1"), "AE");
  assert.equal(bootGame("#XX/R1/1", null), GAME_IDS[0]);
  assert.equal(bootGame("not a hash", null), GAME_IDS[0]);
});

test("every game's file is a shipped dataset that names it back", async () => {
  for (const id of GAME_IDS) {
    const data = JSON.parse(await readFile(`public/${GAME_FILES[id]}`, "utf8"));
    assert.equal(data.id, id);
  }
});
