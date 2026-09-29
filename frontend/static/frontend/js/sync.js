/* sync.js - Gestion du hors-ligne.
   Au retour de la connexion (navigator.onLine / evenement "online"), on
   envoie les ventes en attente (stockees dans IndexedDB) vers
   /api/ventes/sync/ puis on les retire de la file. */
(function () {
  function updateBadge() {
    const el = document.getElementById("online-badge");
    if (!el) return;
    if (navigator.onLine) {
      el.textContent = "En ligne";
      el.className = "badge online";
    } else {
      el.textContent = "Hors-ligne";
      el.className = "badge offline";
    }
  }

  function showBanner(text, type) {
    const el = document.getElementById("sync-banner");
    if (!el) return;
    el.textContent = text;
    el.className = "banner " + (type || "info");
    setTimeout(function () {
      el.className = "banner hidden";
    }, 4500);
  }

  async function syncPending() {
    if (!Store.isAuthed() || !navigator.onLine) {
      updateBadge();
      return;
    }
    await Store.ready;
    const pending = Store.getPendingVentes();
    updateBadge();
    if (!pending.length) return;
    const payload = {
      ventes: pending.map(function (v) {
        return {
          id_local: v.id_local,
          date_heure_creation: v.date_heure_creation || new Date().toISOString(),
          lignes: (v.lignes || []).map(function (l) {
              return { code_barre: l.code_barre || l.id_qr, quantite: l.quantite, id_qr: l.id_qr };
            }),
        };
      }),
    };
    try {
      const r = await Api.request("/ventes/sync/", { method: "POST", body: payload });
      if (r.ok && r.data) {
        const res = r.data.resultats || [];
        res.forEach(function (result) {
          if (result.id_local) Store.removeVente(result.id_local);
        });
        if (res.length) showBanner(res.length + " vente(s) synchronisee(s).", "ok");
      }
    } catch (e) {
      /* reste en attente pour le prochain essai */
    }
    updateBadge();
  }

  window.addEventListener("online", function () {
    updateBadge();
    syncPending();
  });
  window.addEventListener("offline", updateBadge);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      updateBadge();
      syncPending();
    });
  } else {
    updateBadge();
    syncPending();
  }

  window.syncManager = { syncPending: syncPending };
})();
