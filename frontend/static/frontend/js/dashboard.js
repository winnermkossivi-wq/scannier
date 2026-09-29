/* dashboard.js - Page "Tableau de bord" : alertes stock + gestion employes + recapitulatif employes */
(function () {
  const box = document.getElementById("alertes");
  const msg = document.getElementById("alertes-msg");
  const empList = document.getElementById("employes-list");
  const empStatsBox = document.getElementById("employes-stats");
  const empMsg = document.getElementById("emp-msg");

  function show(text, type) {
    if (!text) return (msg.className = "msg hidden");
    msg.textContent = text;
    msg.className = "msg " + (type || "info");
  }
  function showEmp(text, type) {
    if (!text) return (empMsg.className = "msg hidden");
    empMsg.textContent = text;
    empMsg.className = "msg " + (type || "info");
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&", "<": "<", ">": ">", '"': """, "'": "'" }[c];
    });
  }
  function fmt(n) {
    return parseFloat(n || 0).toLocaleString("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  /* ---- Alertes stock ---- */
  async function chargerAlertes() {
    show("Chargement des alertes…", "info");
    try {
      const r = await Api.request("/produits/alertes-stock/", { method: "GET" });
      if (!r.ok) {
        show("Impossible de charger les alertes (code " + r.status + ").", "error");
        return;
      }
      const list = Array.isArray(r.data) ? r.data : [];
      if (!list.length) {
        show("", null);
        box.innerHTML =
          '<p class="text-sm opacity-60">Aucune alerte : stock OK.</p>';
        return;
      }
      show("", null);
      box.innerHTML = list
        .map(function (a) {
          const badge =
            a.urgence === "rupture"
              ? '<span class="badge badge-sm" style="background:#fee2e2;color:#dc2626;">Rupture</span>'
              : '<span class="badge badge-sm" style="background:#fef3c7;color:#d97706;">Stock bas</span>';
          const stock = a.quantite_stock == null ? "?" : a.quantite_stock;
          return (
            '<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 bg-base-200 rounded-xl">' +
            '<div class="flex items-center gap-2">' +
            "<strong>" +
            escapeHtml(a.nom) +
            "</strong> " +
            badge +
            "</div>" +
            '<div class="text-sm opacity-60">Stock : ' +
            stock +
            (a.seuil_alerte != null ? " / seuil " + a.seuil_alerte : "") +
            "</div>" +
            "</div>"
          );
        })
        .join("");
    } catch (e) {
      show("Erreur reseau : " + e.message, "error");
    }
  }

  /* ---- Récapitulatif par employé ---- */
  async function chargerEmployesStats() {
    try {
      const r = await Api.request("/comptes/employes/", { method: "GET" });
      if (!r.ok) {
        empStatsBox.innerHTML = '<p class="text-sm opacity-60">Impossible de charger le récapitulatif.</p>';
        return;
      }
      const list = Array.isArray(r.data) ? r.data : [];
      if (!list.length) {
        empStatsBox.innerHTML = '<p class="text-sm opacity-60">Aucun employe.</p>';
        return;
      }
      empStatsBox.innerHTML = list
        .map(function (e) {
          const roleBadge =
            e.role === "patron"
              ? '<span class="badge badge-sm" style="background:#dbeafe;color:#2563eb;">Patron</span>'
              : '<span class="badge badge-sm" style="background:#f3e8ff;color:#7c3aed;">Employé</span>';
          const statusBadge = e.actif
            ? '<span class="badge badge-sm" style="background:#d1fae5;color:#059669;">Actif</span>'
            : '<span class="badge badge-sm" style="background:#fee2e2;color:#dc2626;">Suspendu</span>';
          const nbVentes = e.nb_ventes || 0;
          const montantTotal = parseFloat(e.montant_total || 0);
          const lastActivite = e.derniere_activite
            ? new Date(e.derniere_activite).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
            : "—";
          return (
            '<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 bg-base-200 rounded-xl gap-2">' +
            '<div class="flex flex-wrap items-center gap-2">' +
            "<strong>" +
            escapeHtml(e.username) +
            "</strong> " +
            roleBadge +
            " " +
            statusBadge +
            "</div>" +
            '<div class="flex flex-wrap items-center gap-4 text-sm">' +
            '<span class="flex items-center gap-1"><svg class="w-4 h-4 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>' +
            nbVentes + " ventes</span>" +
            '<span class="flex items-center gap-1 font-medium text-primary"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>' +
            fmt(montantTotal) + " FCFA</span>" +
            '<span class="opacity-50">Dernière: ' + escapeHtml(lastActivite) + "</span>" +
            "</div>" +
            "</div>"
          );
        })
        .join("");
    } catch (e) {
      empStatsBox.innerHTML = '<p class="text-sm text-error">Erreur de chargement.</p>';
    }
  }

  /* ---- Gestion des employes ---- */
  async function chargerEmployes() {
    try {
      const r = await Api.request("/comptes/employes/", { method: "GET" });
      if (!r.ok) {
        empList.innerHTML = '<p class="text-sm opacity-60">Impossible de charger la liste.</p>';
        return;
      }
      const list = Array.isArray(r.data) ? r.data : [];
      if (!list.length) {
        empList.innerHTML = '<p class="text-sm opacity-60">Aucun employe pour le moment.</p>';
        return;
      }
      empList.innerHTML = list
        .map(function (e) {
          const roleBadge =
            e.role === "patron"
              ? '<span class="badge badge-sm" style="background:#dbeafe;color:#2563eb;">Patron</span>'
              : '<span class="badge badge-sm" style="background:#f3e8ff;color:#7c3aed;">Employe</span>';
          const statusBadge = e.actif
            ? '<span class="badge badge-sm" style="background:#d1fae5;color:#059669;">Actif</span>'
            : '<span class="badge badge-sm" style="background:#fee2e2;color:#dc2626;">Suspendu</span>';
          const deleteBtn =
            e.role !== "patron"
              ? '<button class="btn btn-ghost btn-sm text-error" onclick="window._supprimerEmploye(' + e.id + ')" title="Supprimer"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>'
              : "";
          return (
            '<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 bg-base-200 rounded-xl gap-2">' +
            '<div class="flex flex-wrap items-center gap-2">' +
            "<strong>" +
            escapeHtml(e.username) +
            "</strong> " +
            roleBadge +
            " " +
            statusBadge +
            "</div>" +
            '<div>' +
            deleteBtn +
            "</div>" +
            "</div>"
          );
        })
        .join("");
    } catch (e) {
      empList.innerHTML = '<p class="text-sm text-error">Erreur de chargement.</p>';
    }
  }

  /* Supprimer un employe */
  window._supprimerEmploye = async function (id) {
    if (!confirm("Voulez-vous vraiment supprimer cet employe ?")) return;
    try {
      const r = await Api.request("/comptes/employes/" + id + "/supprimer/", {
        method: "DELETE",
      });
      if (r.ok) {
        showEmp("Employe supprime.", "ok");
        chargerEmployes();
        chargerEmployesStats();
      } else {
        showEmp("Erreur : " + (r.data && r.data.detail ? r.data.detail : "suppression echouee"), "error");
      }
    } catch (e) {
      showEmp("Erreur reseau.", "error");
    }
  };

  /* Modal ajout employe */
  function setupModal() {
    const modal = document.getElementById("modal-add-employe");
    const backdrop = document.getElementById("modal-backdrop");
    const btnAdd = document.getElementById("btn-add-employe");
    const btnCancel = document.getElementById("btn-cancel-employe");
    const form = document.getElementById("form-add-employe");

    function openModal() {
      showEmp("", null);
      form.reset();
      modal.classList.remove("hidden");
    }

    function closeModal() {
      modal.classList.add("hidden");
    }

    if (btnAdd) {
      btnAdd.addEventListener("click", openModal);
    }
    if (btnCancel) {
      btnCancel.addEventListener("click", closeModal);
    }
    if (backdrop) {
      backdrop.addEventListener("click", closeModal);
    }
    if (form) {
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        const username = document.getElementById("emp-username").value.trim();
        const email = document.getElementById("emp-email").value.trim();
        const password = document.getElementById("emp-password").value;
        const role = document.getElementById("emp-role").value;

        if (!username || !password) {
          showEmp("Remplissez tous les champs obligatoires.", "error");
          return;
        }
        if (password.length < 6) {
          showEmp("Le mot de passe doit faire au moins 6 caracteres.", "error");
          return;
        }
        showEmp("Creation en cours…", "info");
        try {
          const body = { username: username, password: password, role: role };
          if (email) body.email = email;
          const r = await Api.request("/comptes/employes/ajouter/", {
            method: "POST",
            body: body,
          });
          if (r.ok) {
            showEmp("Employe cree avec succes !", "ok");
            form.reset();
            closeModal();
            chargerEmployes();
            chargerEmployesStats();
          } else {
            const detail =
              (r.data && r.data.detail) ||
              (r.data && typeof r.data === "object"
                ? Object.values(r.data).flat().join(", ")
                : "Erreur inconnue");
            showEmp("Erreur : " + detail, "error");
          }
        } catch (err) {
          showEmp("Erreur reseau : " + err.message, "error");
        }
      });
    }
  }

  /* ---- Init ---- */
  (async function init() {
    if (!Store.isAuthed()) {
      window.location.href = "/connexion/";
      return;
    }
    await Store.ready;
    chargerAlertes();
    chargerEmployes();
    chargerEmployesStats();
    setupModal();
  })();
})();
})();
