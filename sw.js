// Service worker: persistent cache for the cam artwork only. GitHub Pages
// re-stamps every file's HTTP validators on deploy, so without this each
// deploy makes repeat visitors re-download all PNGs. Cam images are
// byte-deterministic build outputs. Bump CACHE_NAME if ever regenerated.
const CACHE_NAME = "cams-v1";
// opt-in marker bucket, created/deleted by the page. Checked per fetch:
// unregistration can't stop a controlling worker until reload, and a
// module flag wouldn't survive an idle-worker restart
const ENABLED = "cams-on";
const MAX_ENTRIES = 2000; // ≈140 MB; a full AE browse is 1936 files
const TRIM_SLACK = 50; // hysteresis so trim doesn't scan keys() on every put

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys())
        if (name.startsWith("cams-") && name !== CACHE_NAME && name !== ENABLED)
          await caches.delete(name);
      await self.clients.claim();
    })(),
  );
});

function isCamRequest(request) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  return url.origin === self.location.origin && /^\/cams\/.+\.png$/.test(url.pathname);
}

async function trim(cache) {
  const keys = await cache.keys(); // insertion order: oldest first
  if (keys.length <= MAX_ENTRIES + TRIM_SLACK) return;
  for (const key of keys.slice(0, keys.length - MAX_ENTRIES)) await cache.delete(key);
}

self.addEventListener("fetch", (event) => {
  if (!isCamRequest(event.request)) return; // browser default for everything else
  event.respondWith(
    (async () => {
      let cache = null;
      try {
        if (await caches.has(ENABLED)) {
          cache = await caches.open(CACHE_NAME);
          const hit = await cache.match(event.request);
          if (hit) return hit;
        }
      } catch {
        cache = null;
      }
      const response = await fetch(event.request);
      if (cache && response.ok) {
        try {
          await cache.put(event.request, response.clone());
          event.waitUntil(trim(cache).catch(() => {}));
        } catch {
          /* the response still counts even if it can't be stored */
        }
      }
      return response;
    })(),
  );
});
