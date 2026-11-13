/* Атлас эпох: офлайн-оболочка. Данные и страницы — «сначала сеть, потом кэш»; изображения этого сайта — «сначала кэш». */
const VERSION = "atlas-v5-20261113-world-studio";
const SHELL = ["./", "index.html", "eras.js", "atlas.js", "maps.js", "epochs.js", "vendor/leaflet-1.9.4/leaflet.js", "vendor/leaflet-1.9.4/leaflet.css", "data/thumbs.json", "data/eras.json", "data/atlas.json", "manifest.webmanifest",
  "icons/icon-192.png", "img/loc-97683588-carte-d-europe-1769_w1000.jpg"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return; // внешние музейные изображения не кэшируем
  const isImg = /\.(jpe?g|png|webp|avif)$/i.test(url.pathname);
  if (isImg) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); }
      return res;
    })));
  } else {
    e.respondWith(fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match("index.html"))));
  }
});
