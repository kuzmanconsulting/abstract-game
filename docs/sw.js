/* Abstract Reader service worker — offline support. Navigation & data are network-first (stay fresh);
   static assets are cache-first. Bump CACHE to invalidate. */
const CACHE = "ar-v1";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./og.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()).catch(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (req.mode === "navigate") {                       // page: network-first so updates show, cache offline
    e.respondWith(fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put("./", cp)); return r; })
      .catch(() => caches.match("./").then(c => c || caches.match(req))));
    return;
  }
  if (url.pathname.endsWith("data.json") || url.pathname.endsWith("data-lite.json")) {   // corpus: fresh if online
    e.respondWith(fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return r; })
      .catch(() => caches.match(req)));
    return;
  }
  e.respondWith(caches.match(req).then(c => c || fetch(req).then(r => {   // assets/fonts: cache-first
    if (r.ok && (url.origin === location.origin)) { const cp = r.clone(); caches.open(CACHE).then(cc => cc.put(req, cp)); }
    return r;
  })));
});
