/* historique.js - Page "Mes ventes".
   Contrat reel : GET /api/ventes/ -> liste de ventes {id, id_unique,
   montant_total, statut, date_heure_creation, lignes:[...]}. */
(function () {
  const msg = document.getElementById("msg");
  const body = document.getElementById("hist-body");

  function show(text, type) {
    if (!text) return (msg.className = "msg hidden");
    msg.textContent = text;
    msg.className = "msg " + (type || "info");
  }
  function fmt(n) {
    return parseFloat(n || 0).toFixed(2) + " FCFA";
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&", "<": "<", ">": ">", '"': """, "'": "'" }[c];
    });
  }
  function statutFr(s) {
    return { finalisee: "Finalisee", en_cours: "En cours", annulee: "Annulee" }[s] || s;
  }

  function badgeStatut(s) {
    // Blue-only badges
    const map = {
      finalisee: "bg-blue-600 text-white",
      en_cours: "bg-blue-600 text-white",
      annulee: "bg-blue-600 text-white",
    };
    const cls = map[s] || "bg-blue-600 text-white";
    return '<span class="badge ' + cls + '">' + statutFr(s) + "</span>";
  }
  function dateFr(iso) {
    const d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString("fr-FR");
  }

  async function charger() {
    show("Chargement...", "info");
    try {
      const r = await Api.request("/ventes/", { method: "GET" });
      if (!r.ok) {
        show("Impossible de charger l'historique (code " + r.status + ").", "error");
        return;
      }
      const list = Array.isArray(r.data) ? r.data : [];
      show(list.length ? "" : "Aucune vente enregistree.", list.length ? "hidden" : "info");
      if (!list.length) {
        body.innerHTML = '<tr><td colspan="5" style="color:#1e40af;">Aucune vente.</td></tr>';
        return;
      }
      body.innerHTML = list
        .map(function (v) {
          const n = (v.lignes || []).length;
          return (
            '<tr class="animate-fade-in"><td>' +
            escapeHtml(v.id_unique || v.id) +
            "</td><td>" +
            dateFr(v.date_heure_creation) +
            "</td><td>" +
            n +
            "</td><td>" +
            fmt(v.montant_total) +
            "</td><td>" +
            badgeStatut(v.statut) +
            "</td></tr>"
          );
        })
        .join("");
    } catch (e) {
      show("Erreur reseau : " + e.message, "error");
    }
  }

  (async function init() {
    if (!Store.isAuthed()) {
      window.location.href = "/connexion/";
      return;
    }
    await Store.ready;
    charger();
  })();
})();