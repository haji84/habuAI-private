/* Site assets may be available offline after first successful authenticated load. */
const CACHE = 'hub-natural-static-v4-network';
const STATIC = ['./','./index.html','./manifest.webmanifest','./assets/logo.png',
  './assets/icon-192.png','./assets/icon-512.png','./assets/apple-touch-icon.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k.startsWith('hub-natural-') && k !== CACHE).map(k => caches.delete(k))
  )));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  // Installed home screen must not keep serving old 243/249 totals forever.
  // Network-first for the page; only use the last authenticated cache offline.
  if (url.pathname.endsWith('/index.html') || url.pathname.endsWith('/')) {
    event.respondWith(fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(c => c.put(event.request, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(event.request)) || Response.error()));
    return;
  }
  if (url.pathname.endsWith('/data/capture_summary.json')) {
    const stable = new Request(new URL('./data/capture_summary.json', self.registration.scope));
    event.respondWith(fetch(event.request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(c => c.put(stable, copy)));
      }
      return response;
    }).catch(async () => (await caches.match(stable)) || Response.error()));
    return;
  }
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
