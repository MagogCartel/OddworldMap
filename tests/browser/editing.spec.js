import { test, expect } from "@playwright/test";
import { trackErrors, settleAny } from "./helpers.js";

// the page's module singletons, stashed once so every poll below stays a
// synchronous read
async function attach(page) {
  await page.evaluate(async () => {
    const u = (m) => new URL("js/" + m, location.href).href;
    window.__st = (await import(u("state.js"))).state;
    window.__nav = await import(u("navigate.js"));
    window.__model = await import(u("model.js"));
    window.__edits = await import(u("edits.js"));
    window.__applied = location.hash;
    window.addEventListener("hashchange", () => (window.__applied = location.hash));
    const replace = history.replaceState.bind(history);
    history.replaceState = (...args) => {
      replace(...args);
      window.__applied = location.hash;
    };
  });
}
const editOn = (page) => page.evaluate(() => window.__st.edit);

// centre the standing path's first Door and return where it is on the screen. A
// jump's own pushed write is flushed first and the re-apply of a hash it changed
// waited for: a hashchange still queued when the camera is set would re-fit the
// view from under the click that follows
const aimAtDoor = (page) =>
  page.evaluate(async () => {
    const st = window.__st;
    window.__nav.flushHash();
    while (location.hash !== window.__applied)
      await new Promise((r) => window.addEventListener("hashchange", r, { once: true }));
    const t = st.path.tlvs.find((o) => o.name === "Door" && o.fields);
    window.__nav.jumpToTlv(st.data, st.lvl, st.path, t);
    const [cx, cy] = window.__model.markerCentre(t);
    const r = document.getElementById("cv").getBoundingClientRect();
    const { cam } = st;
    return {
      x: r.left + (cx - cam.x) * cam.z,
      y: r.top + (cy - cam.y) * cam.z,
      x1: t.x1,
      y1: t.y1,
      camera: t.fields.camera,
    };
  });

const doorNow = (page, d) =>
  page.evaluate((d) => {
    const st = window.__st;
    const at = (P) => P.tlvs.find((o) => o.name === "Door" && o.x1 === d.x1 && o.y1 === d.y1);
    const t = at(st.path);
    return {
      camera: t.fields.camera,
      toCam: t.extra.to_cam,
      pristineCamera: at(window.__pristine).fields.camera,
      swapped: st.path !== window.__pristine,
      standing: st.data.levels.includes(st.lvl),
      edited: window.__edits.pathEdited(st.path),
    };
  }, d);

test("the mode selects an object, the form edits it, and every surface follows", async ({
  page,
}) => {
  const errors = trackErrors(page);
  await page.goto("/#AE");
  await settleAny(page);
  await attach(page);
  await page.keyboard.press("e");
  await page.waitForFunction(() => window.__st.edit === true);
  await expect(page.locator("#editBtn")).toHaveAttribute("aria-pressed", "true");

  const door = await aimAtDoor(page);
  await page.mouse.click(door.x, door.y);
  await expect(page.locator("#editPanel")).toBeVisible();
  expect(
    await page.evaluate(() => [window.__st.sel.name, window.__st.sel.x1, window.__st.sel.y1]),
  ).toEqual(["Door", door.x1, door.y1]);
  await page.evaluate(() => {
    window.__pristine = window.__st.path;
  });

  const input = page.locator('#editBody input[data-field="camera"]');
  await input.fill(String(door.camera + 1));
  await input.press("Tab");
  await page.waitForFunction((c) => window.__st.sel?.fields.camera === c, door.camera + 1);
  expect(await doorNow(page, door)).toEqual({
    camera: door.camera + 1,
    toCam: door.camera + 1,
    pristineCamera: door.camera,
    swapped: true,
    standing: true,
    edited: true,
  });
  await expect(page.locator("#editBody .ep-shipped")).toContainText(`shipped: ${door.camera}`);

  // a Places hit onto the same path lands on the objects now standing
  await page.fill("#searchInput", "necrum mines");
  await page.waitForSelector("#searchResults .hit");
  await page
    .locator("#searchResults .hit")
    .filter({ has: page.locator(".loc", { hasText: /^AE · MI P1$/ }) })
    .first()
    .click();
  expect((await doorNow(page, door)).camera).toBe(door.camera + 1);

  // a number input takes `e` as an exponent, never as the mode's key
  const again = await aimAtDoor(page); // the jump re-fit the view
  await page.mouse.click(again.x, again.y);
  await expect(page.locator("#editPanel")).toBeVisible();
  await page.locator('#editBody input[data-field="camera"]').focus();
  await page.keyboard.press("e");
  expect(await editOn(page)).toBe(true);

  // the graph covers the map: opening it leaves the mode, and `e` under it is refused
  await page.locator('#editBody input[data-field="camera"]').blur(); // map keys aim at the map
  await page.keyboard.press("Escape");
  await page.keyboard.press("v");
  await page.waitForFunction(() => window.__st.graph === true);
  expect(await editOn(page)).toBe(false);
  await expect(page.locator("#editBtn")).toBeHidden();
  await page.keyboard.press("e");
  expect(await editOn(page)).toBe(false);
  await page.keyboard.press("v");
  await page.waitForFunction(() => window.__st.graph === false);

  // a revert puts the pristine path itself back
  await page.keyboard.press("e");
  await page.waitForFunction(() => window.__st.edit === true);
  const back = await aimAtDoor(page);
  await page.mouse.click(back.x, back.y);
  await page.locator("#editBody .ep-foot .linkbtn", { hasText: "Revert this path" }).click();
  await page.waitForFunction(() => window.__st.path === window.__pristine);
  expect(await page.evaluate(() => window.__edits.pathEdited(window.__st.path))).toBe(false);
  expect(errors).toEqual([]);
});

test("an embed shows the shipped map: no button, and the key is refused", async ({ page }) => {
  const errors = trackErrors(page);
  await page.goto("/?embed=1#AE");
  await settleAny(page);
  await attach(page);
  await expect(page.locator("#editBtn")).toBeHidden();
  await page.keyboard.press("e");
  expect(await editOn(page)).toBe(false);
  expect(errors).toEqual([]);
});
