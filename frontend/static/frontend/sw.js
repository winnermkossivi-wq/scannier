const CACHE_NAME = 'scannier-v1';
const STATIC_CACHE = 'scannier-static-v1';
const DYNAMIC_CACHE = 'scannier-dynamic-v1';
const API_CACHE = 'scannier-api-v1';

const STATIC_ASSETS = [
  '/connexion/',
  '/tableau-de-bord/',
  '/vente/nouvelle/',
  '/produits/',
  '/historique/',
  '/employes/',
  '/confidentialite/',
  '/static/frontend/css/style.css',
  '/static/frontend/js/app.js',
  '/static/frontend/js/api.js',
  '/static/frontend/js/storage.js',
  '/static/frontend/js/mock.js',
  '/static/frontend/js/sync.js',
  '/static/frontend/js/bluetooth.js',
  '/static/frontend/js/pdfprint.js',
  '/static/frontend/js/dashboard.js',
  '/static/frontend/js/historique.js',
  '/static/frontend/js/login.js',
  '/static/frontend/js/produits.js',
  '/static/frontend/js/tous_produits.js',
  '/static/frontend/js/vente.js',
  '/static/frontend/js/ticket.js',
  '/static/frontend/manifest.json',
];

const CACHE_STRATEGIES = {
  static: 'stale-while-revalidate',
  api: 'network-first',
  navigation: 'network-first',
  fonts: 'cache-first',
  images: 'cache-first',
};

const MAX_DYNAMIC_CACHE_SIZE = 50;
const MAX_API_CACHE_SIZE = 100;
const CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000;

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/') ||
         url.pathname.endsWith('.css') ||
         url.pathname.endsWith('.js') ||
         url.pathname.endsWith('.png') ||
         url.pathname.endsWith('.jpg') ||
         url.pathname.endsWith('.jpeg') ||
         url.pathname.endsWith('.svg') ||
         url.pathname.endsWith('.woff') ||
         url.pathname.endsWith('.woff2') ||
         url.pathname.endsWith('.ttf') ||
         url.pathname.endsWith('.eot') ||
         url.pathname.endsWith('.ico');
}

function isApiRequest(url) {
  return url.pathname.startsWith('/api/');
}

function isNavigationRequest(request) {
  return request.mode === 'navigate' ||
         (request.method === 'GET' && request.headers.get('accept')?.includes('text/html'));
}

function isFontRequest(url) {
  return url.pathname.match(/\.(woff|woff2|ttf|eot)$/);
}

function isImageRequest(url) {
  return url.pathname.match(/\.(png|jpg|jpeg|svg|gif|webp|ico)$/);
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

async function networkFirst(request, cacheName, maxSize) {
  const cache = await caches.open(cacheName);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
      await limitCacheSize(cache, maxSize);
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    if (isNavigationRequest(request)) {
      return caches.match('/connexion/') || new Response('Offline', { status: 503 });
    }
    return new Response(JSON.stringify({ error: 'Offline', message: 'Données non disponibles hors ligne' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request).then(networkResponse => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(() => cachedResponse);

  return cachedResponse || fetchPromise;
}

async function limitCacheSize(cache, maxSize) {
  const keys = await cache.keys();
  if (keys.length > maxSize) {
    await cache.delete(keys[0]);
    return limitCacheSize(cache, maxSize);
  }
}

async function cleanOldCaches() {
  const cacheNames = await caches.keys();
  const validCaches = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];
  await Promise.all(
    cacheNames
      .filter(name => !validCaches.includes(name))
      .map(name => caches.delete(name))
  );
}

async function handleStaticAsset(request) {
  return staleWhileRevalidate(request, STATIC_CACHE);
}

async function handleApiRequest(request) {
  if (request.method !== 'GET') {
    return fetch(request);
  }
  return networkFirst(request, API_CACHE, MAX_API_CACHE_SIZE);
}

async function handleNavigationRequest(request) {
  return networkFirst(request, DYNAMIC_CACHE, MAX_DYNAMIC_CACHE_SIZE);
}

async function handleFontRequest(request) {
  return cacheFirst(request, STATIC_CACHE);
}

async function handleImageRequest(request) {
  return cacheFirst(request, STATIC_CACHE);
}

self.addEventListener('install', event => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      await cache.addAll(STATIC_ASSETS);
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    (async () => {
      await cleanOldCaches();
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== location.origin) {
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(handleStaticAsset(request));
    return;
  }

  if (isApiRequest(url)) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  if (isNavigationRequest(request)) {
    event.respondWith(handleNavigationRequest(request));
    return;
  }

  if (isFontRequest(url)) {
    event.respondWith(handleFontRequest(request));
    return;
  }

  if (isImageRequest(url)) {
    event.respondWith(handleImageRequest(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE));
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      (async () => {
        await caches.delete(STATIC_CACHE);
        await caches.delete(DYNAMIC_CACHE);
        await caches.delete(API_CACHE);
        event.ports[0].postMessage({ success: true });
      })()
    );
  }
});

self.addEventListener('periodicsync', event => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncOfflineData());
  }
});

async function syncOfflineData() {
  try {
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({ type: 'SYNC_TRIGGERED' });
    });
  } catch (error) {
    console.error('Sync failed:', error);
  }
}

self.addEventListener('push', event => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/static/frontend/icons/icon-192x192.png',
    badge: '/static/frontend/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    data: data.data || {},
    actions: data.actions || [],
    requireInteraction: data.requireInteraction || false,
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action) {
    event.waitUntil(
      clients.openWindow(event.action)
    );
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url === event.notification.data.url && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(event.notification.data.url || '/connexion/');
    })
  );
});

console.log('[SW] Service Worker Scannier chargé - Version:', CACHE_NAME);