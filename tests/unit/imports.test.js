import { test } from "node:test";
import assert from "node:assert/strict";

// The regression guard for the whole suite: these modules must never touch the
// DOM at import time, or nothing but a browser session would catch it.
test("pure modules import in bare Node", async () => {
  for (const mod of [
    "annotations",
    "config",
    "data",
    "demo",
    "fields",
    "state",
    "util",
    "model",
    "settings",
    "searchquery",
    "placesearch",
    "pathorder",
    "glossary",
    "census",
    "placesummary",
    "typeinfo",
    "worldgraph",
  ]) {
    const m = await import(`../../public/js/${mod}.js`);
    assert.ok(Object.keys(m).length > 0, `${mod}.js has exports`);
  }
});
