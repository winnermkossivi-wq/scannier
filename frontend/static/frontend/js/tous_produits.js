/* tous_produits.js - Page "Tous les produits" (patron / superuser) - codes-barres.
   Contrat reel : GET /api/produits/tous/ -> liste de produits
   {id, id_qr, code_barre, nom, prix, cree_par_nom, cree_par_username, marchand_nom}. */
(function () {
  const msg = document.getElementById("msg");
  const body = document.getElementById("tous-body");
  const bulkQty = document.getElementById("bulk-qty");
  const bulkBtn = document.getElementById("bulk-print");
  function barcodeValue(p){ return p.code_barre || p.barcode_value || p.id_qr; }

  function show(text, type) {
    if (!text) return (msg.className = "msg hidden");
    msg.textContent = text;
    msg.className = "msg " + (type || "info");
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmtPrix(p) {
    return parseFloat(p || 0).toFixed(2) + " FCFA";
  }
  function createur(p) {
    return p.cree_par_nom || p.cree_par_username || "—";
  }

  async function charger() {
    show("Chargement...", "info");
    try {
      const r = await Api.request("/produits/tous/", { method: "GET" });
      if (!r.ok) {
        show("Accès refusé ou erreur (code " + r.status + ").", "error");
        return;
      }
      const list = Array.isArray(r.data) ? r.data : [];
      show(list.length ? "" : "Aucun produit.", list.length ? "hidden" : "info");
      if (!list.length) {
        body.innerHTML =
          '<tr><td colspan="8" style="color:var(--muted);">Aucun produit.</td></tr>';
        return;
      }
      body.innerHTML = "";
      list.forEach(function (p) {
        const tr = document.createElement("tr");
        const code = barcodeValue(p);
        tr.innerHTML =
          "<td>" + escapeHtml(p.nom) + "</td>" +
          "<td>" + fmtPrix(p.prix) + "</td>" +
          '<td><svg class="barcode-mini" data-code="' + escapeHtml(code) + '"></svg><div style="font-size:0.6rem;word-break:break-all;">' + escapeHtml(code) + '</div></td>' +
          "<td>" + escapeHtml(createur(p)) + "</td>" +
          "<td>" + escapeHtml(p.marchand_nom || "—") + "</td>" +
          '<td><input type="number" class="qty-input" value="1" min="1" max="100" style="max-width:70px;"></td>' +
          '<td><button class="btn-print no-print">Imprimer (PDF)</button></td>' +
          '<td><button class="btn-del btn btn-error btn-xs">Suppr.</button></td>';
        const qtyInput = tr.querySelector(".qty-input");
        tr._produit = p;
        // rendu code-barres traits
        const svg = tr.querySelector(".barcode-mini");
        if (svg && typeof JsBarcode !== "undefined") {
          try { JsBarcode(svg, String(code), { format:"CODE128", width:1.2, height:30, displayValue:false, margin:2 }); } catch(e){ svg.outerHTML = '<span style="font-size:0.6rem;">'+escapeHtml(code)+'</span>'; }
        }
        tr.querySelector(".btn-print").addEventListener("click", async function () {
          const okPdf = await window.imprimerProduitPDF(p, qtyInput.value);
          if (!okPdf) show("Endpoint PDF indisponible (mode simulation).", "info");
        });
        tr.querySelector(".btn-del").addEventListener("click", async function () {
          if (!confirm("Supprimer '"+p.nom+"' ("+code+") ?")) return;
          try {
            const r = await Api.request("/produits/" + p.id + "/", { method: "DELETE" });
            if (r.ok || r.status===204 || r.status===200) { tr.remove(); show(r.data && r.data.detail ? r.data.detail : "Produit supprime.", r.status===200?"info":"ok"); if (!body.querySelector("tr")) body.innerHTML='<tr><td colspan="8" style="color:var(--muted);">Aucun produit.</td></tr>'; }
            else if (r.status===401) { show("Session expirée (401) — reconnectez-vous.", "error"); setTimeout(function(){ Store.clearAuth(); window.location.href="/connexion/"; }, 1200); }
            else show("Echec ("+r.status+")", "error");
          } catch(e){ show("Erreur: "+e.message, "error"); }
        });
        body.appendChild(tr);
      });
    } catch (e) {
      show("Erreur réseau : " + e.message, "error");
    }
  }

  if (bulkBtn)
    bulkBtn.addEventListener("click", async function () {
      const qty = parseInt(bulkQty.value, 10) || 1;
      const rows = body.querySelectorAll("tr");
      let i = 0;
      for (const tr of rows) {
        const p = tr._produit;
        if (!p) continue;
        await window.imprimerProduitPDF(p, qty);
        i++;
      }
      show(i + " lot(s) d'étiquettes envoyé(s) à l'impression.", "ok");
    });

  (async function init() {
    if (!Store.isAuthed()) {
      window.location.href = "/connexion/";
      return;
    }
    if (!Store.isPatronOrSuper()) {
      window.location.href = "/produits/";
      return;
    }
    await Store.ready;
    charger();
  })();
})();
