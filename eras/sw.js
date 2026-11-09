/* City on Paper: bounded/offline-safe atlas PWA.
 * The atlas shell and research metadata are cached for offline navigation.
 * Do NOT masquerade an HTML page as a missing JSON or JavaScript file.
 * Cached photos and map tiles are opportunistic and bounded.
 */
"use strict";
const PREFIX = "city-on-paper-eras-";
const VERSION = "20261109-v5";
const SHELL_CACHE = PREFIX + "shell-" + VERSION;
const IMAGE_CACHE = PREFIX + "images-" + VERSION;
const IMAGE_MAX_ENTRIES = 96;
const SHELL = [
  "./", "index.html", "eras.js", "atlas.js", "maps.js", "epochs.js",
  "three-epochs.js", "chronoscope.js", "curatorial-desk.js",
  "city-lab.js", "cartography.js", "journey.js",
  "three-epochs.css", "chronoscope.css", "curatorial-desk.css",
  "city-lab.css", "cartography.css", "journey.css",
  "vendor/leaflet-1.9.4/leaflet.js", "vendor/leaflet-1.9.4/leaflet.css",
  "data/thumbs.json", "data/eras.json", "data/atlas.json",
  "data/map-evidence.json", "manifest.webmanifest",
  "icons/icon-192.png", "img/loc-97683588-carte-d-europe-1769_w1000.jpg"
];
const IMAGE_RE = /\.(?:jpe?g|png|webp|avif)$/i;

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  // Caches belong to the whole origin. Never erase unrelated museum/app caches.
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys
      .filter(key => (
        (key.startsWith(PREFIX) && key !== SHELL_CACHE && key !== IMAGE_CACHE)
        || /^atlas-v\d+-/.test(key) // migrate only the old atlas SW cache
      ))
      .map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

async function putBoundedImage(request, response) {
  if (!response.ok || !String(response.headers.get("Content-Type") || "")
    .toLowerCase().startsWith("image/")) return;
  const cache = await caches.open(IMAGE_CACHE);
  // Cache insertion order is predictable; keep only the last 96 images/tiles.
  const existing = await cache.match(request);
  if (!existing) {
    const keys = await cache.keys();
    while (keys.length >= IMAGE_MAX_ENTRIES) {
      const oldest = keys.shift();
      if (oldest) await cache.delete(oldest);
    }
  }
  await cache.put(request, response);
}

async function respond(event) {
  const request = event.request;
  const isImage = IMAGE_RE.test(new URL(request.url).pathname);
  if (isImage) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
      const fresh = await fetch(request);
      if (fresh.ok) {
        // The response can be used immediately; the image cache is best-effort.
        try { await putBoundedImage(request, fresh.clone()); }
        catch (err) { console.warn("Image cache write skipped:", err); }
      }
      return fresh;
    } catch (_error) {
      return new Response("Изображение недоступно без сети", {
        status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" }
      });
    }
  }
  try {
    const fresh = await fetch(request);
    if (fresh.ok && fresh.type !== "opaque") {
      try {
        const cache = await caches.open(SHELL_CACHE);
        await cache.put(request, fresh.clone());
      } catch (err) { console.warn("Atlas shell cache write skipped:", err); }
    }
    return fresh;
  } catch (_error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    if (request.mode === "navigate") {
      const home = await caches.match(new URL("./", self.registration.scope));
      if (home) return home;
    }
    // An offline JS/JSON/CSS miss must be a real failure, never index.html.
    return new Response("Атлас: нет сети или локальной копии файла", {
      status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" }
    });
  }
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  event.respondWith(respond(event));
});
