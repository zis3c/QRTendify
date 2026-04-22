// {% load static %}
// Keep cache version in sync with behavior changes.
const CACHE_NAME = 'qrtendify-v11';
const OFFLINE_URL = '{% url "offline" %}';
const assetsToCache = [
    '/',
    OFFLINE_URL,
    '{% static "js/app.js" %}',
    '{% static "js/qrcode.min.js" %}',
    '{% static "images/logo_QRTendify.svg" %}'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return Promise.all(
                assetsToCache.map(url => {
                    return cache.add(url).catch(e => {
                        console.warn(`SW Install Warning: Failed to cache ${url}.`, e);
                        return Promise.resolve();
                    });
                })
            );
        })
    );
    // Activate new worker immediately.
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const requestUrl = new URL(event.request.url);
    const isSameOrigin = requestUrl.origin === self.location.origin;
    const request = event.request;
    const destination = request.destination;

    if (!isSameOrigin) {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    return await fetch(request);
                } catch (error) {
                    const cache = await caches.open(CACHE_NAME);
                    const cachedResponse = await cache.match(OFFLINE_URL);
                    return cachedResponse || new Response("<h1>Offline UI Missing. Please go online and reload.</h1>", { status: 503, headers: { 'Content-Type': 'text/html' } });
                }
            })()
        );
    }
    // Network-first for scripts/styles so refresh always gets latest UI.
    else if (destination === 'style' || destination === 'script') {
        event.respondWith(
            (async () => {
                const cache = await caches.open(CACHE_NAME);
                try {
                    const networkResponse = await fetch(request);
                    cache.put(request, networkResponse.clone());
                    return networkResponse;
                } catch (error) {
                    const cachedResponse = await cache.match(request);
                    return cachedResponse || Response.error();
                }
            })()
        );
    }
    // Cache-first for static media.
    else if (destination === 'image' || destination === 'font') {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                return cachedResponse || fetch(request);
            })
        );
    }
});
