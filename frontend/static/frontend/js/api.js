/* api.js - Client HTTP minimal pour l'API Scannier.
   - Ajoute le token JWT (Bearer) automatiquement.
   - En mode simulation (USE_MOCK), bascule sur MockAPI si l'API
     reelle repond pas / repond 404 (endpoints pas encore crees).
   - Affiche une banniere reseau visible en cas d'echec reseau. */
(function () {
  let networkErrorBanner = null;

  function ensureNetworkBanner() {
    if (networkErrorBanner) return networkErrorBanner;
    networkErrorBanner = document.getElementById('network-banner');
    if (!networkErrorBanner) {
      networkErrorBanner = document.createElement('div');
      networkErrorBanner.id = 'network-banner';
      networkErrorBanner.className = 'hidden';
      networkErrorBanner.innerHTML = '<div class="flex items-center justify-between bg-amber-500 text-white text-center py-2 px-4 text-sm"><span>Connexion perdue — la vente sera synchronisée plus tard</span><button onclick="this.parentElement.parentElement.classList.add(\'hidden\')" class="ml-2 font-bold text-white hover:text-amber-100">✕</button></div>';
      document.body.prepend(networkErrorBanner);
    }
    return networkErrorBanner;
  }

  function showNetworkError(show) {
    const banner = ensureNetworkBanner();
    if (show) {
      banner.classList.remove('hidden');
      // Auto-masquer apres 5 secondes
      clearTimeout(banner._hideTimer);
      banner._hideTimer = setTimeout(function() {
        banner.classList.add('hidden');
      }, 5000);
    } else {
      banner.classList.add('hidden');
    }
  }

  async function request(path, options) {
    options = options || {};
    const method = (options.method || "GET").toUpperCase();
    const url = window.API_BASE + path;
    const headers = { "Content-Type": "application/json" };
    const token = Store.getToken();
    if (token) headers["Authorization"] = "Bearer " + token;

    const tryReal = async function () {
      const resp = await fetch(url, {
        method: method,
        headers: headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
      if (resp.ok) {
        let data = null;
        try {
          data = await resp.json();
        } catch (e) {
          data = null;
        }
        showNetworkError(false);
        return { ok: true, status: resp.status, data: data };
      }
      return { ok: false, status: resp.status };
    };

    if (!window.USE_MOCK) {
      try {
        return await tryReal();
      } catch (e) {
        showNetworkError(true);
        return { ok: false, status: 0, error: e.message };
      }
    }

    function toResult(m) {
      return {
        ok: m.status >= 200 && m.status < 300,
        status: m.status,
        data: m.data,
      };
    }

    try {
      const r = await tryReal();
      if (r.ok) return r;
      return toResult(await MockAPI.handle(path, method, options.body));
    } catch (e) {
      return toResult(await MockAPI.handle(path, method, options.body));
    }
  }

  // Synchronise le catalogue local avec l'API des que possible.
  // Contrat reel : GET /api/produits/catalogue-sync/ -> {produits:[...]}
  async function syncCatalogue() {
    try {
      const r = await request("/produits/catalogue-sync/", { method: "GET" });
      if (r.ok && r.data && Array.isArray(r.data.produits)) {
        Store.setCatalogue(r.data.produits);
        return r.data.produits;
      }
    } catch (e) {
      /* reste sur le cache local IndexedDB */
    }
    return Store.getCatalogue();
  }

  window.Api = {
    request: request,
    syncCatalogue: syncCatalogue,
    login: function (username, password, role) {
      return request("/comptes/login/", {
        method: "POST",
        body: { username: username, password: password, role: role },
      });
    },
  };
})();
