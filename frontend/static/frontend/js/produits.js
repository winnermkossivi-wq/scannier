/* produits.js - Page "Mes produits" : liste, ajout local, generation/impression code-barres.
   Le code-barres est recupere via l'API (/api/produits/<id>/barcode/ -> image base64 PNG, fallback /qr/). */
(function () {
  const REFERENCE = [
    { nom: "Tomates 1kg", prix: "500.00" },
    { nom: "Oignons 1kg", prix: "400.00" },
    { nom: "Pommes de terre 1kg", prix: "350.00" },
    { nom: "Huile de palme 1L", prix: "1500.00" },
    { nom: "Farine 1kg", prix: "300.00" },
    { nom: "Oeufs (x12)", prix: "900.00" },
  ];

  const msg = document.getElementById("msg");
  const grid = document.getElementById("product-grid");

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

  function enLigne() {
    return navigator.onLine;
  }

  function lireStock() {
    // si modal Ajouter est ouvert, lit ses champs ref
    const modalAjouter = document.getElementById("modal-ajouter");
    const isAjouterOpen = modalAjouter && !modalAjouter.classList.contains("hidden");
    if (isAjouterOpen) {
      const cb = document.getElementById("suivre-stock-ref");
      const suivre = cb && cb.checked;
      if (!suivre) return { suivre_stock: false, quantite_stock: null, seuil_alerte: null };
      const qte = parseInt(document.getElementById("stock-qte-ref").value, 10);
      const seuil = parseInt(document.getElementById("stock-seuil-ref").value, 10);
      return { suivre_stock: true, quantite_stock: isNaN(qte) ? 0 : qte, seuil_alerte: isNaN(seuil) ? null : seuil };
    }
    const cb = document.getElementById("suivre-stock");
    const suivre = cb && cb.checked;
    if (!suivre) return { suivre_stock: false, quantite_stock: null, seuil_alerte: null };
    const qte = parseInt(document.getElementById("stock-qte").value, 10);
    const seuil = parseInt(document.getElementById("stock-seuil").value, 10);
    return {
      suivre_stock: true,
      quantite_stock: isNaN(qte) ? 0 : qte,
      seuil_alerte: isNaN(seuil) ? null : seuil,
    };
  }

  function stockLineHtml(p) {
    if (!p || !p.suivre_stock) return "";
    let urgence = null;
    if (p.quantite_stock !== null && p.quantite_stock <= 0) urgence = "rupture";
    else if (p.quantite_stock !== null && p.seuil_alerte !== null && p.quantite_stock <= p.seuil_alerte)
      urgence = "seuil";
    const badge = urgence
      ? '<span class="badge ' + (urgence === "rupture" ? "rupture" : "seuil") + '">' +
        (urgence === "rupture" ? "Rupture" : "Stock bas") + "</span> "
      : "";
    const txt =
      "Stock : " + (p.quantite_stock == null ? "?" : p.quantite_stock) +
      (p.seuil_alerte != null ? " / seuil " + p.seuil_alerte : "");
    return '<div class="stock-line' + (urgence ? " " + urgence : "") + '">' + badge + txt + "</div>";
  }

  function barcodeValue(produit) {
    return produit.code_barre || produit.barcode_value || produit.id_qr;
  }
  function renderBarcodeSync(container, produit) {
    const val = barcodeValue(produit);
    container.innerHTML = "";
    if (typeof JsBarcode !== "undefined") {
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.className = "barcode-svg";
      container.appendChild(svg);
      try { JsBarcode(svg, String(val), { format: "CODE128", width: 2, height: 55, displayValue: true, fontSize: 11, margin: 2 }); return "svg"; } catch (e) {}
    }
    if (typeof QRCode !== "undefined") {
      try { new QRCode(container, { text: String(val), width: 160, height: 160 }); return "qr"; } catch (e) {}
    }
    container.textContent = "[Code-barres " + val + "]";
    return null;
  }
  async function renderBarcode(container, produit) {
    const val = barcodeValue(produit);
    // 1) rendu immediat cote client pour voir les traits tout de suite
    renderBarcodeSync(container, produit);
    let src = null;
    // seulement pour produits serveur (id numerique), on tente l'image serveur en arriere-plan
    if (String(produit.id).startsWith("local-")) return src;
    try {
      const r = await Api.request("/produits/" + produit.id + "/barcode/", { method: "GET" });
      const b64 = r.ok && r.data && (r.data.barcode_base64_png || r.data.qr_base64_png);
      if (b64) {
        src = "data:image/png;base64," + b64;
        // remplace le svg par l'image serveur (plus nette pour impression)
        container.innerHTML = "";
        const img = document.createElement("img");
        img.src = src;
        img.alt = "Code-barres " + val;
        img.className = "barcode-img";
        container.appendChild(img);
      }
    } catch (e) { /* garde le svg deja affiche */ }
    return src;
  }
  // compat alias
  const renderQR = renderBarcode;

  function printLabel(produit, barSrc) {
    const val = barcodeValue(produit);
    const w = window.open("", "_blank");
    const html =
      "<!DOCTYPE html><html><head><meta charset='utf-8'><title>" +
      escapeHtml(produit.nom) +
      "</title><style>" +
      "body{font-family:system-ui,sans-serif;text-align:center;padding:8px;}" +
      ".nom{font-size:22px;font-weight:800;margin-top:8px;}" +
      ".prix{font-size:20px;color:#b00;font-weight:700;margin:4px 0;}" +
      ".id{font-size:11px;color:#666;margin-top:4px;word-break:break-all;}" +
      "img{max-width:260px;max-height:100px;} svg{max-width:260px;}" +
      "@media print{body{padding:0;}}" +
      "</style></head><body>" +
      (barSrc ? '<img src="' + barSrc + '">' : '<svg id="bc"></svg>') +
      '<div class="nom">' + escapeHtml(produit.nom) + "</div>" +
      '<div class="prix">' + fmtPrix(produit.prix) + "</div>" +
      '<div class="id">Code: ' + escapeHtml(val) + "</div>" +
      "</body></html>";
    w.document.write(html);
    w.document.close();
    if (!barSrc && typeof JsBarcode !== "undefined") {
      try { JsBarcode(w.document.getElementById("bc"), String(val), { format: "CODE128", width: 2, height: 60, displayValue: true }); } catch (e) {}
    } else if (!barSrc && typeof QRCode !== "undefined") {
      w.document.getElementById("bc").outerHTML = "<div id='q'></div>";
      new QRCode(w.document.getElementById("q"), { text: String(val), width: 170, height: 170 });
    }
    setTimeout(function () {
      w.print();
    }, 350);
  }

  function renderProducts(list) {
    if (!list || !list.length) {
      grid.innerHTML = '<p style="color:var(--muted);">Aucun produit pour l\'instant.</p>';
      return;
    }
    grid.innerHTML = "";
    list.forEach(function (p) {
      const card = document.createElement("div");
      card.className =
        "product-card etiquette card card-compact bg-base-100 shadow-md rounded-2xl animate-fade-in";
      card.innerHTML =
        '<div class="pname">' +
        escapeHtml(p.nom) +
        "</div>" +
        '<div class="pprice">' +
        fmtPrix(p.prix) +
        "</div>" +
        '<div class="barcode-box qr-box"></div>' +
        '<div class="pid">Code: ' +
        escapeHtml(barcodeValue(p)) +
        "</div>" +
        stockLineHtml(p) +
        '<div class="print-toolbar no-print">' +
        '<label class="qty-label">Exemplaires' +
        '<input type="number" class="qty-input" value="1" min="1" max="100"></label>' +
        "</div>";
      // --- App-like: options dans bottom sheet sur mobile, visibles direct sur desktop ---
      function openOptionsSheet(){
        const qtyVal = (card.querySelector(".qty-input") && card.querySelector(".qty-input").value) || "1";
        const html = '<div class="flex items-center gap-3 mb-2"><div class="flex-1"><div class="font-bold">'+escapeHtml(p.nom)+'</div><div class="text-sm opacity-70">'+fmtPrix(p.prix)+' • Code: '+escapeHtml(barcodeValue(p))+'</div></div></div>'
          + '<label class="flex items-center gap-2 text-sm">Exemplaires <input type="number" id="sheet-qty-'+p.id+'" value="'+qtyVal+'" min="1" max="100" class="input input-bordered input-sm rounded-full w-24"></label>'
          + '<div class="grid grid-cols-2 gap-2 mt-3">'
          + '<button id="sheet-print-'+p.id+'" class="btn bg-violet-600 hover:bg-violet-700 text-white rounded-full">Imprimer (PDF)</button>'
          + '<button id="sheet-preview-'+p.id+'" class="btn btn-ghost rounded-full">Aperçu</button>'
          + '<button id="sheet-stock-'+p.id+'" class="btn btn-ghost rounded-full">Stock</button>'
          + '<button id="sheet-del-'+p.id+'" class="btn btn-error rounded-full">Supprimer</button>'
          + '</div>';
        window.showProductSheet(html);
        setTimeout(function(){
          const q=document.getElementById('sheet-qty-'+p.id);
          document.getElementById('sheet-print-'+p.id).onclick=async function(){ const qty=parseInt(q.value,10)||1; const ok=await window.imprimerProduitPDF(p,qty); if(!ok){ const src=await renderBarcode(card.querySelector(".barcode-box"), p); printLabel(p,src);} window.closeProductSheet(); };
          document.getElementById('sheet-preview-'+p.id).onclick=async function(){ const src=await renderBarcode(card.querySelector(".barcode-box"), p); printLabel(p,src); window.closeProductSheet(); };
          document.getElementById('sheet-stock-'+p.id).onclick=function(){ window.closeProductSheet(); editerStock(p, card); card.scrollIntoView({behavior:'smooth'}); };
          document.getElementById('sheet-del-'+p.id).onclick=async function(){ window.closeProductSheet(); btnSuppr.click(); };
        }, 50);
      }
      const btn = document.createElement("button");
      btn.className = "btn btn-primary btn-sm rounded-full no-print inline-flex";
      btn.style.marginTop = "8px";
      btn.textContent = "Imprimer (PDF)";
      btn.onclick = async function () {
        const qty = parseInt(card.querySelector(".qty-input").value, 10) || 1;
        const okPdf = await window.imprimerProduitPDF(p, qty);
        if (!okPdf) {
          const src = await renderBarcode(card.querySelector(".barcode-box"), p);
          printLabel(p, src);
        }
      };
      const btnApercu = document.createElement("button");
      btnApercu.className = "btn btn-ghost btn-sm rounded-full no-print inline-flex";
      btnApercu.style.marginTop = "8px";
      btnApercu.textContent = "Aperçu";
      btnApercu.onclick = async function () {
        const src = await renderBarcode(card.querySelector(".barcode-box"), p);
        printLabel(p, src);
      };
      const btnStock = document.createElement("button");
      btnStock.className = "btn btn-ghost btn-sm rounded-full no-print inline-flex";
      btnStock.style.marginTop = "8px";
      btnStock.textContent = "Stock";
      btnStock.onclick = function () {
        editerStock(p, card);
      };
      const btnSuppr = document.createElement("button");
      btnSuppr.className = "btn btn-error btn-sm rounded-full no-print inline-flex";
      btnSuppr.style.marginTop = "8px";
      btnSuppr.textContent = "Supprimer";
      btnSuppr.onclick = async function () {
        if (!confirm("Supprimer '" + p.nom + "' (" + barcodeValue(p) + ") ?\nCette action est irreversible (le code-barres sera supprime).")) return;
        if (String(p.id).startsWith("local-")) {
          const cat = Store.getCatalogue() || [];
          Store.setCatalogue(cat.filter(function (x) { return String(x.id) !== String(p.id); }));
          card.remove();
          show("Produit supprime (local).", "ok");
          if ((Store.getCatalogue()||[]).length===0) renderProducts([]);
          return;
        }
        try {
          const r = await Api.request("/produits/" + p.id + "/", { method: "DELETE" });
          if (r.ok || r.status===204 || r.status===200) {
            const cat = Store.getCatalogue() || [];
            Store.setCatalogue(cat.filter(function(x){ return String(x.id)!==String(p.id); }));
            card.remove();
            Api.syncCatalogue().then(function(){ const c2 = Store.getCatalogue()||[]; if (c2.find(function(x){ return String(x.id)===String(p.id); })) { Store.setCatalogue(c2.filter(function(x){ return String(x.id)!==String(p.id); })); } }).catch(function(){});
            if ((Store.getCatalogue()||[]).length===0) renderProducts([]);
            show(r.data && r.data.detail ? r.data.detail : "Produit supprime.", r.status===200?"info":"ok");
          } else if (r.status===401) {
            show("Session expirée (401) — reconnectez-vous.", "error");
            setTimeout(function(){ Store.clearAuth(); window.location.href="/connexion/"; }, 1200);
          } else {
            show("Suppression echouee (" + r.status + ").", "error");
          }
        } catch (e) {
          show("Erreur reseau : " + e.message, "error");
        }
      };
      // bouton visible seulement sur mobile pour ouvrir le sheet
      const btnOptions = document.createElement("button");
      btnOptions.className = "btn btn-ghost btn-sm rounded-full w-full mt-2 hidden";
      btnOptions.textContent = "Voir options ›";
      btnOptions.onclick = openOptionsSheet;
      // carte cliquable désactivée sur téléphone (tout visible comme PC)
      card.style.cursor = "default";
      card.appendChild(btn);
      card.appendChild(btnApercu);
      card.appendChild(btnStock);
      card.appendChild(btnSuppr);
      card.appendChild(btnOptions);
      // compat: certains CSS attendent .qr-box, on garde les deux classes
      const box = card.querySelector(".barcode-box");
      if (box) box.classList.add("qr-box");
      grid.appendChild(card);
      renderBarcode(box, p);
    });
  }

  function editerStock(p, card) {
    if (card.querySelector(".stock-editor")) return;
    const ed = document.createElement("div");
    ed.className = "stock-editor no-print";
    ed.innerHTML =
      '<label class="qty-label"><input type="checkbox" class="e-suivre"' +
      (p.suivre_stock ? " checked" : "") +
      "> Suivre le stock</label>" +
      '<input type="number" class="e-qte" value="' +
      (p.quantite_stock == null ? 0 : p.quantite_stock) +
      '" min="0" placeholder="Stock">' +
      '<input type="number" class="e-seuil" value="' +
      (p.seuil_alerte == null ? "" : p.seuil_alerte) +
      '" min="0" placeholder="Seuil">' +
      '<button class="e-save">Enregistrer</button>';
    card.appendChild(ed);
    ed.querySelector(".e-save").onclick = async function () {
      const suivre = ed.querySelector(".e-suivre").checked;
      const qte = parseInt(ed.querySelector(".e-qte").value, 10);
      const seuil = parseInt(ed.querySelector(".e-seuil").value, 10);
      const data = {
        suivre_stock: suivre,
        quantite_stock: suivre ? (isNaN(qte) ? 0 : qte) : null,
        seuil_alerte: suivre ? (isNaN(seuil) ? null : seuil) : null,
      };
      if (p.id && enLigne() && !String(p.id).startsWith("local-")) {
        try {
          const r = await Api.request("/produits/" + p.id + "/", { method: "PATCH", body: data });
          if (r.ok && r.data) {
            const cat = Store.getCatalogue() || [];
            const idx = cat.findIndex(function (x) {
              return String(x.id) === String(p.id);
            });
            if (idx >= 0) {
              cat[idx] = Object.assign({}, cat[idx], r.data);
              Store.setCatalogue(cat);
            }
            ed.remove();
            renderProducts(Store.getCatalogue());
            show("Stock mis à jour (serveur).", "ok");
            return;
          }
        } catch (e) {
          /* repli local */
        }
      }
      p.suivre_stock = suivre;
      p.quantite_stock = suivre ? (isNaN(qte) ? 0 : qte) : null;
      p.seuil_alerte = suivre ? (isNaN(seuil) ? null : seuil) : null;
      const cat = Store.getCatalogue() || [];
      const idx = cat.findIndex(function (x) {
        return String(x.id) === String(p.id);
      });
      if (idx >= 0) {
        cat[idx] = p;
        Store.setCatalogue(cat);
      }
      ed.remove();
      renderProducts(Store.getCatalogue());
      show("Stock mis à jour (local).", "ok");
    };
  }

  function initRefSelect() {
    const sel = document.getElementById("ref-select");
    if (!sel) return;
    sel.innerHTML = REFERENCE.map(function (r, i) {
      return '<option value="' + i + '">' + escapeHtml(r.nom) + " - " + r.prix + "</option>";
    }).join("");
  }

  async function addProduit(nom, prix, codeBarre, stock) {
    stock = stock || { suivre_stock: false, quantite_stock: null, seuil_alerte: null };
    const suivre = !!stock.suivre_stock;
    const body = {
      nom: nom,
      prix: String(prix),
      code_barre: codeBarre || undefined,
      actif: true,
      suivre_stock: suivre,
      quantite_stock: suivre ? stock.quantite_stock : null,
      seuil_alerte: suivre ? stock.seuil_alerte : null,
    };
    if (enLigne()) {
      try {
        const r = await Api.request("/produits/creer/", { method: "POST", body: body });
        if (r.ok && r.data) {
          await Api.syncCatalogue();
          renderProducts(Store.getCatalogue());
          show("Produit créé (serveur) : " + nom, "ok");
          return;
        }
      } catch (e) {
        /* repli hors-ligne */
      }
    }
    const p = {
      id: "local-" + Date.now(),
      code_barre: codeBarre || "CB-" + Date.now(),
      id_qr: codeBarre || "CB-" + Date.now(),
      nom: nom,
      prix: String(prix),
      suivre_stock: suivre,
      quantite_stock: body.quantite_stock,
      seuil_alerte: body.seuil_alerte,
      actif: true,
    };
    const cat = Store.getCatalogue() || [];
    cat.push(p);
    Store.setCatalogue(cat);
    Store.addProduitLocal(p);
    show("Produit ajouté (stockage local, hors-ligne) : " + nom, "ok");
    renderProducts(Store.getCatalogue());
  }

  // Modals Ajouter / Generer (comme Ajouter employé / Saisie manuelle)
  function openAjouter(){ const m=document.getElementById("modal-ajouter"); if(m) m.classList.remove("hidden"); document.body.style.overflow="hidden"; }
  function closeAjouter(){ const m=document.getElementById("modal-ajouter"); if(m) m.classList.add("hidden"); document.body.style.overflow=""; }
  function openGenerer(){ const m=document.getElementById("modal-generer"); if(m) m.classList.remove("hidden"); document.body.style.overflow="hidden"; }
  function closeGenerer(){ const m=document.getElementById("modal-generer"); if(m) m.classList.add("hidden"); document.body.style.overflow=""; }
  if (document.getElementById("mode-ref")) document.getElementById("mode-ref").addEventListener("click", openAjouter);
  if (document.getElementById("mode-libre")) document.getElementById("mode-libre").addEventListener("click", openGenerer);
  const ajBackdrop=document.getElementById("modal-ajouter-backdrop");
  if(ajBackdrop) ajBackdrop.addEventListener("click", closeAjouter);
  const genBackdrop=document.getElementById("modal-generer-backdrop");
  if(genBackdrop) genBackdrop.addEventListener("click", closeGenerer);
  const ajClose=document.getElementById("modal-ajouter-close");
  if(ajClose) ajClose.addEventListener("click", closeAjouter);
  const ajX=document.getElementById("modal-ajouter-x");
  if(ajX) ajX.addEventListener("click", closeAjouter);
  const genClose=document.getElementById("modal-generer-close");
  if(genClose) genClose.addEventListener("click", closeGenerer);
  const genX=document.getElementById("modal-generer-x");
  if(genX) genX.addEventListener("click", closeGenerer);
  document.addEventListener("keydown", function(e){
    if(e.key==="Escape"){
      const maj=document.getElementById("modal-ajouter");
      const mgen=document.getElementById("modal-generer");
      if(maj && !maj.classList.contains("hidden")) closeAjouter();
      if(mgen && !mgen.classList.contains("hidden")) closeGenerer();
    }
  });
  if (document.getElementById("add-ref"))
    document.getElementById("add-ref").addEventListener("click", function () {
       const r = REFERENCE[parseInt(document.getElementById("ref-select").value, 10)];
       if (r) { addProduit(r.nom, r.prix, null, lireStock()); closeAjouter(); }
    });
  if (document.getElementById("add-libre"))
    document.getElementById("add-libre").addEventListener("click", function () {
      const nom = document.getElementById("lib-nom").value.trim();
      const prix = document.getElementById("lib-prix").value;
      const id = document.getElementById("lib-id").value.trim();
      if (!nom || prix === "") {
        show("Nom et prix requis.", "error");
        return;
      }
      addProduit(nom, prix, id, lireStock()); closeGenerer();
    });

  const suivreCb = document.getElementById("suivre-stock");
  if (suivreCb) suivreCb.addEventListener("change", function () {
      const f = document.getElementById("stock-fields");
      if (f) f.classList.toggle("hidden", !suivreCb.checked);
    });
  const suivreCbRef = document.getElementById("suivre-stock-ref");
  if (suivreCbRef) suivreCbRef.addEventListener("change", function () {
      const f = document.getElementById("stock-fields-ref");
      if (f) f.classList.toggle("hidden", !suivreCbRef.checked);
    });

  (async function init() {
    if (!Store.isAuthed()) {
      window.location.href = "/connexion/";
      return;
    }
    await Store.ready;
    initRefSelect();
    await Api.syncCatalogue();
    renderProducts(Store.getCatalogue());
  })();
})();
