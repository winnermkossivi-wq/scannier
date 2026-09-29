/* vente.js - Page "Nouvelle vente" (code-barres).
   Fonctionne en mode en ligne (API directe) ET hors-ligne (file IndexedDB
   rejouee vers /api/ventes/sync/ au retour de la connexion). */
(function () {
  let localVente = null;
  let lignes = [];
  let scanner = null;
  let scanning = false;
  let lastScan = { id: null, t: 0 };
  let audioCtx = null;

  const msg = document.getElementById("msg");
  const linesBody = document.getElementById("lines-body");
  const linesBodyDesktop = document.getElementById("lines-body-desktop");
  const linesBodySheet = document.getElementById("lines-body-sheet");
  const countEl = document.getElementById("lignes-count");
  const totalEl = document.getElementById("total");
  const scanBadge = document.getElementById("scan-badge");
  const toastContainer = document.getElementById("toast-container");

  function show(text, type) {
    if (!text) {
      msg.className = "msg hidden";
      return;
    }
    msg.textContent = text;
    msg.className = "msg " + (type || "info");
  }

  function fmt(n) {
    return parseFloat(n || 0).toFixed(2);
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&", "<": "<", ">": ">", '"': """, "'": "'" }[c];
    });
  }

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "local-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  function enLigne() {
    return navigator.onLine;
  }

  function updateScanBadge() {
    const count = lignes.reduce((sum, l) => sum + (l.quantite || 1), 0);
    if (scanBadge) {
      if (count > 0) {
        scanBadge.textContent = count > 99 ? "99+" : count;
        scanBadge.classList.remove("hidden");
      } else {
        scanBadge.classList.add("hidden");
        scanBadge.textContent = "0";
      }
    }
    if (countEl) countEl.textContent = count;
  }

  function renderLines() {
    const htmlDesktop = !lignes.length
      ? '<tr><td colspan="4" style="color:var(--muted);">Aucune ligne pour le moment.</td></tr>'
      : lignes.map(function (l) {
          return '<tr class="animate-fade-in"><td>' + escapeHtml(l.nom) + "</td><td>" + fmt(l.prix) + "</td><td>" + l.quantite + "</td><td>" + fmt(parseFloat(l.prix) * l.quantite) + "</td></tr>";
        }).join("");
    const htmlMobile = !lignes.length
      ? '<tr><td colspan="3" style="color:var(--muted);">Aucune ligne pour le moment.</td></tr>'
      : lignes.map(function (l) {
          return '<tr class="animate-fade-in"><td>' + escapeHtml(l.nom) + "</td><td>" + l.quantite + "</td><td>" + fmt(parseFloat(l.prix) * l.quantite) + "</td></tr>";
        }).join("");
    if (linesBody) linesBody.innerHTML = htmlMobile;
    if (linesBodyDesktop) linesBodyDesktop.innerHTML = htmlDesktop;
    if (linesBodySheet) linesBodySheet.innerHTML = htmlMobile;
    updateScanBadge();
    const total = lignes.reduce(function (s, l) {
      return s + parseFloat(l.prix) * l.quantite;
    }, 0);
    if (totalEl) {
      totalEl.textContent = fmt(total);
      totalEl.classList.remove("pop");
      void totalEl.offsetWidth;
      totalEl.classList.add("pop");
    }
  }

  function syncLocalToView() {
    lignes = (localVente && localVente.lignes) || [];
    renderLines();
  }

  function basculerHorsLigne() {
    if (localVente && !localVente.pending) {
      localVente.serverId = null;
      localVente.id_local = uuid();
      localVente.pending = true;
      Store.saveVente(localVente);
    }
  }

  async function ensureVente() {
    if (localVente) return localVente;
    if (enLigne()) {
      try {
        const r = await Api.request("/ventes/", { method: "POST", body: {} });
        if (r.ok && r.data && r.data.id) {
          localVente = {
            id_local: uuid(),
            serverId: r.data.id,
            statut: "en_cours",
            lignes: [],
            pending: false,
          };
          Store.saveVente(localVente);
          return localVente;
        }
      } catch (e) {
        /* passe en mode hors-ligne */
      }
    }
    localVente = {
      id_local: uuid(),
      serverId: null,
      statut: "en_cours",
      lignes: [],
      pending: true,
    };
    Store.saveVente(localVente);
    show("Mode hors-ligne : la vente sera synchronisée au retour du réseau.", "info");
    return localVente;
  }

  function resolveProduit(value) {
    return Store.findInCatalogue(value);
  }

  function barcodeValue(produit) {
    return produit.code_barre || produit.id_qr;
  }

  function afficherAvertissementStock(produit) {
    const w = document.getElementById("stock-warn");
    if (!w) return;
    let urgence = null;
    const stock = produit.quantite_stock == null ? null : Number(produit.quantite_stock);
    if (produit.suivre_stock && stock !== null && stock <= 0) urgence = "rupture";
    else if (produit.suivre_stock && stock !== null && produit.seuil_alerte !== null && stock <= Number(produit.seuil_alerte))
      urgence = "seuil";
    if (!urgence) {
      w.className = "stock-warn hidden";
      return;
    }
    w.className = "stock-warn " + urgence;
    w.textContent =
      (urgence === "rupture" ? "⚠ Rupture de stock" : "⚠ Stock bas") +
      " : " + produit.nom + " (stock = " + (stock == null ? "?" : stock) + ").";
    setTimeout(function () {
      w.className = "stock-warn hidden";
    }, 4000);
  }

  function playSound(type) {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      if (type === "success") {
        osc.frequency.value = 880;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.15);
      } else if (type === "unknown") {
        osc.frequency.value = 220;
        osc.type = "square";
        gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
        setTimeout(() => {
          const osc2 = audioCtx.createOscillator();
          const gain2 = audioCtx.createGain();
          osc2.connect(gain2);
          gain2.connect(audioCtx.destination);
          osc2.frequency.value = 165;
          osc2.type = "square";
          gain2.gain.setValueAtTime(0.1, audioCtx.currentTime);
          gain2.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
          osc2.start();
          osc2.stop(audioCtx.currentTime + 0.3);
        }, 120);
      }
    } catch (e) {
      console.warn("Audio non disponible:", e);
    }
  }

  function showToast(message, type, duration) {
    if (!toastContainer) return;
    const toast = document.createElement("div");
    toast.className = "toast animate-fade-in px-4 py-2.5 rounded-xl shadow-lg text-sm font-medium flex items-center gap-2 max-w-xs w-full";
    const icon = type === "success" ? "✓" : type === "error" ? "✕" : type === "warning" ? "⚠" : "ℹ";
    const bg = type === "success" ? "bg-green-600 text-white" : type === "error" ? "bg-red-600 text-white" : type === "warning" ? "bg-amber-600 text-white" : "bg-blue-600 text-white";
    toast.className += " " + bg;
    toast.innerHTML = '<span class="flex-shrink-0">' + icon + '</span><span class="flex-1 truncate">' + escapeHtml(message) + '</span>';
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("opacity-0", "translate-x-4", "transition-all", "duration-300");
      setTimeout(() => toast.remove(), 300);
    }, duration || 1800);
  }

  async function ajouterLigne(value, quantite) {
    await Store.ready;
    quantite = parseInt(quantite, 10) || 1;
    const produit = resolveProduit(value);
    if (!produit) {
      playSound("unknown");
      showToast("Produit inconnu : " + value + " — créez-le ?", "warning", 3000);
      return;
    }
    const code = barcodeValue(produit);
    afficherAvertissementStock(produit);
    if (localVente && !localVente.pending && enLigne()) {
      try {
        const r = await Api.request("/ventes/" + localVente.serverId + "/lignes/", {
          method: "POST",
          body: { code_barre: code, id_qr: code, quantite: quantite },
        });
        if (r.ok) {
          pushLocalLine(code, produit.nom, produit.prix, quantite);
          Store.saveVente(localVente);
          syncLocalToView();
          playSound("success");
          showToast(produit.nom + " ajouté — " + fmt(produit.prix) + " FCFA", "success");
          return;
        }
      } catch (e) {
        basculerHorsLigne();
      }
    }
    pushLocalLine(code, produit.nom, produit.prix, quantite);
    Store.saveVente(localVente);
    syncLocalToView();
    playSound("success");
    showToast(produit.nom + " ajouté (hors-ligne) — " + fmt(produit.prix) + " FCFA", "success");
  }

  function pushLocalLine(code, nom, prix, quantite) {
    const exist = localVente.lignes.find(function (l) {
      return (l.code_barre || l.id_qr) === code;
    });
    if (exist) exist.quantite += quantite;
    else
      localVente.lignes.push({
        code_barre: code,
        id_qr: code,
        nom: nom,
        prix: prix,
        quantite: quantite,
      });
  }

  function handleScan(decodedText) {
    const now = Date.now();
    if (lastScan.id === decodedText && now - lastScan.t < 2000) return;
    lastScan = { id: decodedText, t: now };
    ajouterLigne(decodedText, 1);
  }

  function buildTicket(lines, total, hash, idUnique, date) {
    return {
      id_unique: idUnique || localVente.id_local,
      lignes: lines.map(function (l) {
        return { nom: l.nom, prix: l.prix, quantite: l.quantite };
      }),
      total: fmt(total),
      hash_preuve: hash,
      date_heure: date || new Date().toISOString(),
    };
  }

  function randomHash() {
    let h = "";
    const c = "0123456789abcdef";
    for (let i = 0; i < 64; i++) h += c[(Math.random() * 16) | 0];
    return h;
  }

  async function finaliser() {
    await ensureVente();
    if (localVente && !localVente.pending && enLigne()) {
      try {
        const r = await Api.request("/ventes/" + localVente.serverId + "/finaliser/", {
          method: "POST",
          body: {},
        });
        if (r.ok && r.data) {
          const ls = (r.data.lignes || []).map(function (l) {
            return {
              nom: l.produit_nom,
              prix: l.prix_unitaire_snapshot,
              quantite: l.quantite,
            };
          });
          Store.setLastTicket(
            buildTicket(ls, r.data.montant_total, r.data.hash_preuve, r.data.id_unique)
          );
          Store.removeVente(localVente.id_local);
          window.location.href = "/vente/ticket/";
          return;
        }
      } catch (e) {
        basculerHorsLigne();
      }
    }
    const total = lignes.reduce(function (s, l) {
      return s + parseFloat(l.prix) * l.quantite;
    }, 0);
    localVente.statut = "finalisee";
    Store.saveVente(localVente);
    Store.setLastTicket(
      buildTicket(lignes, total, randomHash(), null, new Date().toISOString())
    );
    window.location.href = "/vente/ticket/";
  }

  async function annuler() {
    if (localVente && !localVente.pending && enLigne()) {
      try {
        await Api.request("/ventes/" + localVente.serverId + "/annuler/", {
          method: "POST",
          body: {},
        });
      } catch (e) {}
      Store.removeVente(localVente.id_local);
    } else if (localVente) {
      Store.removeVente(localVente.id_local);
    }
    window.location.href = "/historique/";
  }

  function startCameraScanner() {
    if (scanning) return;
    if (typeof Html5Qrcode === "undefined") {
      show("Librairie de scan non chargée.", "error");
      return;
    }
    const readerDiv = document.getElementById("reader");
    if (!readerDiv) return;
    readerDiv.classList.remove("hidden");
    readerDiv.innerHTML = "";
    scanning = true;
    scanner = new Html5Qrcode("reader");
    const config = {
      fps: 10,
      qrbox: { width: 250, height: 120 },
      aspectRatio: 1.777,
      disableFlip: true,
      rememberLastUsedCamera: true,
    };
    scanner.start(
      { facingMode: "environment" },
      config,
      (decodedText) => {
        handleScan(decodedText);
      },
      (err) => {
        // scan error, ignore
      }
    ).catch((err) => {
      show("Impossible de démarrer la caméra : " + err.message, "error");
      readerDiv.classList.add("hidden");
      scanning = false;
    });
  }

  function stopCameraScanner() {
    if (!scanner || !scanning) return;
    scanner.stop().catch(() => {}).finally(() => {
      scanning = false;
      const readerDiv = document.getElementById("reader");
      if (readerDiv) readerDiv.classList.add("hidden");
    });
  }

  const scanCameraBtn = document.getElementById("scan-camera");
  if (scanCameraBtn) {
    scanCameraBtn.addEventListener("click", function () {
      if (scanning) {
        stopCameraScanner();
      } else {
        startCameraScanner();
      }
    });
  }

  const scanPhotoBtn = document.getElementById("scan-photo-fallback");
  const scanPhotoInput = document.getElementById("scan-photo-input");
  if (scanPhotoBtn && scanPhotoInput) {
    scanPhotoBtn.addEventListener("click", function () {
      stopCameraScanner();
      scanPhotoInput.click();
    });
    scanPhotoInput.addEventListener("change", async function (e) {
      const file = e.target.files[0];
      if (!file) return;
      if (typeof Html5Qrcode === "undefined") {
        show("Librairie de scan non chargée.", "error");
        return;
      }
      show("Analyse de la photo...", "info");
      try {
        const tempScanner = new Html5Qrcode("reader");
        const result = await tempScanner.scanFile(file, true);
        handleScan(result);
        showToast("Produit détecté : " + result, "info");
      } catch (err) {
        show("Aucun code-barres détecté sur cette photo. Réessayez ou utilisez la saisie manuelle.", "error");
      }
      scanPhotoInput.value = "";
    });
  }

  document.getElementById("manual-add").addEventListener("click", function () {
    const id = document.getElementById("manual-id").value.trim();
    const q = document.getElementById("manual-qte").value;
    if (id) ajouterLigne(id, q);
  });

  document.getElementById("finalize-btn").addEventListener("click", finaliser);
  document.getElementById("cancel-btn").addEventListener("click", annuler);

  document.getElementById("reset-btn").addEventListener("click", async function () {
    if (localVente) {
      Store.removeVente(localVente.id_local);
    }
    localVente = null;
    lignes = [];
    await ensureVente();
    syncLocalToView();
    show("Nouvelle vente prête.", "info");
  });

  document.addEventListener("visibilitychange", function () {
    if (document.hidden && scanning) {
      stopCameraScanner();
    }
  });

  window.addEventListener("beforeunload", function () {
    if (scanning) stopCameraScanner();
  });

  (async function init() {
    if (!Store.isAuthed()) {
      window.location.href = "/connexion/";
      return;
    }
    await Store.ready;
    await Api.syncCatalogue();
    await ensureVente();
    syncLocalToView();
  })();
})();