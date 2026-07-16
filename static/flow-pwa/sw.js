const CACHE_PREFIX = 'flow-canonical-pwa-';
const CACHE_VERSION = 'v10';
const CACHE_NAME = `${CACHE_PREFIX}${CACHE_VERSION}`;
const APP_SHELL = [
  '/',
  '/static/flow-pwa/app.js?v=8',
  '/static/flow-pwa/manifest.webmanifest',
  '/static/flow-pwa/icon-16.png',
  '/static/flow-pwa/icon-32.png',
  '/static/flow-pwa/icon-192.png',
  '/static/flow-pwa/icon-512.png',
  '/static/flow-pwa/icon-512-maskable.png',
  '/static/flow-pwa/apple-touch-icon.png',
  '/favicon.ico',
  '/static/flow-pwa/splash-iphone-1290x2796.png',
  '/static/flow-pwa/splash-iphone-2796x1290.png',
  '/static/flow-pwa/splash-ipad-2048x2732.png',
  '/static/flow-pwa/splash-ipad-2732x2048.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(
      APP_SHELL.map(asset => new Request(asset, { cache: 'reload' }))
    ))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys
        .filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
        .map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
