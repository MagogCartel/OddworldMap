import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// The backlog is hand-kept and its index is a denormalization: an item's
// state is written both in the item and in backlog/README.md, and the items
// address each other by path. Nothing regenerates any of it, so these are
// the checks that keep it honest.

const dir = fileURLToPath(new URL("../../backlog/", import.meta.url));
const read = (name) => readFileSync(join(dir, name), "utf8");
const items = readdirSync(dir)
  .filter((f) => f !== "README.md")
  .sort();
const index = read("README.md");
const idOf = (f) => Number(f.slice(5, 8));

const STATUS = ["open", "undecided", "deferred", "ongoing", "shipped", "retired", "closed"];
// hashes belonging to another repository, listed so every other one has to
// resolve here — an unresolvable hash is a typo, not a foreign pin
const FOREIGN_PINS = new Set([
  "e2badb8df", // alive_reversing master, the tree the released editor pins
]);
const SECTION_BY_STATUS = {
  undecided: "Undecided",
  deferred: "Deferred",
  closed: "Closed",
  shipped: "Finished",
  retired: "Finished",
};
const STATUS_SECTIONS = new Set(Object.values(SECTION_BY_STATUS));
const statusOf = (f) => /^\*\*Status:\*\* (\S+)/m.exec(read(f))?.[1];
const bulletsFor = (f) => [
  // [^\]] keeps this to the bullet's own leading link, so an item cited
  // inside another item's line is not mistaken for a second listing.
  ...index.matchAll(new RegExp(`^- \\[\\*\\*(\\d+)\\.\\*\\* [^\\]]*\\]\\(${f}\\).*$`, "gm")),
];
const sectionAt = (offset) => {
  const headings = [...index.slice(0, offset).matchAll(/^## (.+)$/gm)];
  return headings[headings.length - 1]?.[1];
};

test("item filenames are one unbroken numbered sequence", () => {
  const ids = [];
  for (const f of items) {
    assert.match(f, /^item-\d{3}-[a-z0-9-]+\.md$/, `${f} is named item-NNN-slug.md`);
    ids.push(idOf(f));
  }
  ids.sort((a, b) => a - b);
  const run = ids.map((_, i) => i + 1);
  assert.deepEqual(ids, run, "ids run from 1 with no gaps and no duplicates");
});

test("each item's heading carries its own id", () => {
  for (const f of items) {
    assert.match(read(f), new RegExp(`^# ${idOf(f)}\\. \\S`), `${f} opens with "# ${idOf(f)}. "`);
  }
});

test("each item declares a status from the closed set", () => {
  for (const f of items) {
    const status = statusOf(f);
    assert.ok(status, `${f} has a Status line`);
    assert.ok(STATUS.includes(status), `${f} claims "${status}", not one of ${STATUS.join(", ")}`);
  }
});

test("shipped and retired items carry a completion date", () => {
  for (const f of items) {
    const status = statusOf(f);
    if (status !== "shipped" && status !== "retired") continue;
    assert.match(
      read(f),
      new RegExp(`^\\*\\*Status:\\*\\* ${status} \\d{4}-\\d{2}-\\d{2}(?:\\s|$)`, "m"),
      `${f} dates its ${status} status`,
    );
  }
});

test("the index lists every item once, and agrees with what it claims", () => {
  for (const f of items) {
    const bullet = bulletsFor(f);
    assert.equal(bullet.length, 1, `${f} has exactly one index bullet`);
    assert.equal(Number(bullet[0][1]), idOf(f), `${f}'s bullet is numbered ${idOf(f)}`);
    const date = /^\*\*Status:\*\* \S+ (\d{4}-\d{2}-\d{2})/m.exec(read(f));
    if (date) assert.ok(bullet[0][0].includes(date[1]), `${f}'s bullet carries its ${date[1]}`);
  }
});

test("each index bullet agrees with its status section", () => {
  for (const f of items) {
    const status = statusOf(f);
    assert.ok(status, `${f} has a Status line`);
    const bullet = bulletsFor(f);
    assert.equal(bullet.length, 1, `${f} has exactly one index bullet`);
    const section = sectionAt(bullet[0].index);
    assert.ok(section, `${f} sits under an index section`);
    const expected = SECTION_BY_STATUS[status];
    if (expected) {
      assert.equal(section, expected, `${f} is ${status} but sits under ${section}`);
    } else {
      assert.ok(!STATUS_SECTIONS.has(section), `${f} is ${status} but sits under ${section}`);
    }
  }
});

test("the index states the status vocabulary the items are held to", () => {
  // the vocabulary is stated twice, as this set and as prose in the README.
  // Anchoring on the **Status:** paragraph scopes the read to the run it
  // introduces, so only that list can feed the comparison.
  const block = /\*\*Status:\*\*[^\n]*:\n\n((?:- `[a-z]+`[^\n]*\n)+)/.exec(index);
  assert.ok(block, "the index introduces the status list");
  const listed = [...block[1].matchAll(/^- `([a-z]+)`/gm)].map((m) => m[1]);
  assert.deepEqual(listed, STATUS, "README.md's status list is the checked set, in order");
});

test("Next up contains unique active items", () => {
  // the capture ends with the bullet run, so the list is bounded by its own
  // shape rather than by the prose that follows it.
  const block = /^\*\*Next up\*\*:\n\n((?:- .*\n)+)/m.exec(index);
  assert.ok(block, "the index has a Next up block");
  const seen = new Set();
  for (const [, f] of block[1].matchAll(/\]\((item-[^)]+\.md)\)/g)) {
    assert.ok(items.includes(f), `Next up links to an item file, not ${f}`);
    assert.ok(!seen.has(f), `Next up lists ${f} only once`);
    seen.add(f);
    const status = statusOf(f);
    assert.ok(status === "open" || status === "ongoing", `Next up lists ${f}, which is ${status}`);
  }
});

test("every relative link in the backlog resolves", () => {
  for (const f of [...items, "README.md"]) {
    for (const [, target] of read(f).matchAll(/\]\((?!https?:)([^)#]+)(?:#[^)]*)?\)/g)) {
      assert.ok(existsSync(join(dir, target)), `${f} links to ${target}, which is not there`);
    }
  }
});

test("every commit hash the backlog cites has been pushed", (t) => {
  const git = (...args) =>
    execFileSync("git", args, {
      cwd: dir,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  const ran = (...args) => {
    try {
      git(...args);
      return true;
    } catch {
      return false;
    }
  };
  // A shallow checkout cannot answer this: the commits are simply absent, so
  // every hash would fail. CI checks out at depth 1, which makes this a local gate.
  if (
    !ran("rev-parse", "--verify", "origin/main") ||
    git("rev-parse", "--is-shallow-repository") === "true"
  ) {
    return t.skip("needs a full clone with an origin/main to check against");
  }
  const cited = new Set();
  for (const f of [...items, "README.md"]) {
    for (const [, hash] of read(f).matchAll(/`([0-9a-f]{7,40})`/g)) cited.add(hash);
  }
  for (const hash of cited) {
    if (FOREIGN_PINS.has(hash)) continue;
    assert.ok(ran("cat-file", "-e", `${hash}^{commit}`), `${hash} is cited but is no commit here`);
    assert.ok(
      ran("merge-base", "--is-ancestor", hash, "origin/main"),
      `${hash} is cited but not pushed`,
    );
  }
});
