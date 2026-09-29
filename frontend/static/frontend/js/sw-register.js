(function () {
  if (!('serviceWorker' in navigator)) {
    console.log('[SW] Service Worker non supporté');
    return;
  }

  const SW_URL = '/static/frontend/sw.js';
  const isLocalhost = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
  const isSecure = window.location.protocol === 'https:' || isLocalhost;

  if (!isSecure) {
    console.warn('[SW] Service Worker nécessite HTTPS (ou localhost)');
    return;
  }

  let registration = null;
  let updateFound = false;

  async function registerSW() {
    try {
      registration = await navigator.serviceWorker.register(SW_URL, {
        scope: '/',
        updateViaCache: 'none',
      });

      console.log('[SW] Enregistré avec succès:', registration.scope);

      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (!newWorker) return;

        updateFound = true;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[SW] Nouvelle version disponible');
            showUpdateNotification();
          }
        });
      });

      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (refreshing) return;
        refreshing = true;
        window.location.reload();
      });

      await checkForUpdates();

      if ('periodicSync' in registration) {
        try {
          await registration.periodicSync.register('sync-data', {
            minInterval: 24 * 60 * 60 * 1000,
          });
        } catch (e) {
          console.log('[SW] Periodic sync non disponible:', e.name);
        }
      }

    } catch (error) {
      console.error('[SW] Erreur enregistrement:', error);
    }
  }

  async function checkForUpdates() {
    if (registration) {
      try {
        await registration.update();
      } catch (error) {
        console.error('[SW] Erreur vérification mise à jour:', error);
      }
    }
  }

  function showUpdateNotification() {
    const banner = document.getElementById('sw-update-banner');
    const btn = document.getElementById('sw-update-btn');
    const dismiss = document.getElementById('sw-dismiss-btn');

    if (banner) {
      banner.classList.remove('hidden');
      if (btn) {
        btn.onclick = () => {
          if (registration && registration.waiting) {
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
          }
        };
      }
      if (dismiss) {
        dismiss.onclick = () => banner.classList.add('hidden');
      }
    }
  }

  function sendMessage(type, data = {}) {
    if (registration && registration.active) {
      registration.active.postMessage({ type, ...data });
    }
  }

  function getVersion() {
    return new Promise((resolve) => {
      if (registration && registration.active) {
        const channel = new MessageChannel();
        channel.port1.onmessage = (e) => resolve(e.data.version);
        registration.active.postMessage({ type: 'GET_VERSION' }, [channel.port2]);
      } else {
        resolve(null);
      }
    });
  }

  async function clearCache() {
    if (registration && registration.active) {
      const channel = new MessageChannel();
      return new Promise((resolve) => {
        channel.port1.onmessage = (e) => resolve(e.data.success);
        registration.active.postMessage({ type: 'CLEAR_CACHE' }, [channel.port2]);
      });
    }
    return false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerSW);
  } else {
    registerSW();
  }

  setInterval(checkForUpdates, 60 * 60 * 1000);

  window.SWRegistration = {
    registration: () => registration,
    update: checkForUpdates,
    getVersion,
    clearCache,
    sendMessage,
  };
})();