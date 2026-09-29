/* mock.js - Simulation de l'API Scannier (utilisee uniquement quand
   window.USE_MOCK est a true, c'est-a-dire quand l'API reel n'est pas
   disponible). ATTENTION : les chemins et les formes de reponse ci-dessous
   MIRRENT EXACTEMENT le contrat de l'API reelle (voir scannier/urls.py,
   ventes/views.py, produits/views.py) afin que le code frontend teste le
   meme contrat dans les deux modes. */
(function () {
  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx".replace(/[x]/g, function () {
      return ((Math.random() * 16) | 0).toString(16);
    }) + "-" + Date.now();
  }

  function fakeJwt(role, nom) {
    function b64(obj) {
      return btoa(JSON.stringify(obj))
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");
    }
    const header = b64({ alg: "HS256", typ: "JWT" });
    const payload = b64({ role: role, nom: nom, sub: nom, iat: Date.now() });
    return header + "." + payload + ".mock-signature";
  }

  function seedCatalogue() {
    return [
      { id: 1, id_qr: "PRD-1001", code_barre: "3017620422003", nom: "Savon de marseille", prix: "150.00", reference: "", reference_nom: "", quantite_stock: 40, suivre_stock: false, seuil_alerte: null, actif: true },
      { id: 2, id_qr: "PRD-1002", code_barre: "5449000000996", nom: "Huile d'olive 1L", prix: "1200.00", reference: "", reference_nom: "", quantite_stock: 25, suivre_stock: true, seuil_alerte: 10, actif: true },
      { id: 3, id_qr: "PRD-1003", code_barre: "3560071094000", nom: "Riz 5kg", prix: "3500.00", reference: "", reference_nom: "", quantite_stock: 60, suivre_stock: true, seuil_alerte: 55, actif: true },
      { id: 4, id_qr: "PRD-1004", code_barre: "8000500037560", nom: "Sucre 1kg", prix: "600.00", reference: "", reference_nom: "", quantite_stock: 50, suivre_stock: true, seuil_alerte: 5, actif: true },
      { id: 5, id_qr: "PRD-1005", code_barre: "7613035989535", nom: "Lait concentre", prix: "450.00", reference: "", reference_nom: "", quantite_stock: 0, suivre_stock: true, seuil_alerte: null, actif: true },
    ];
  }

  function ensureCatalogue() {
    let cat = Store.getCatalogue();
    if (!cat) {
      cat = seedCatalogue();
      Store.setCatalogue(cat);
    }
    // Normalise pour garantir la presence des champs de suivi de stock et code-barres
    cat = cat.map(function (p) {
      if (p.suivre_stock === undefined) p.suivre_stock = false;
      if (p.seuil_alerte === undefined) p.seuil_alerte = null;
      if (!p.code_barre) p.code_barre = p.id_qr ? String(p.id_qr).replace(/[^0-9]/g,'').padEnd(13,'0').slice(0,13) : "0000000000000";
      if (!p.id_qr) p.id_qr = p.code_barre;
      return p;
    });
    Store.setCatalogue(cat);
    return cat;
  }

  function computeTotal(lignes) {
    return lignes
      .reduce(function (s, l) {
        return s + parseFloat(l.prix) * l.quantite;
      }, 0)
      .toFixed(2);
  }

  function randomHash() {
    let h = "";
    const chars = "0123456789abcdef";
    for (let i = 0; i < 64; i++) h += chars[(Math.random() * 16) | 0];
    return h;
  }

  function ok(data, status) {
    return Promise.resolve({ status: status || 200, data: data });
  }

  function venteOut(v) {
    return {
      id: v.serverId || v.id_local,
      id_unique: v.id_unique || v.id_local,
      marchand: 1,
      marchand_nom: "Boutique " + (Store.getNom() || ""),
      employe: 1,
      employe_username: v.createur_nom || Store.getNom() || "",
      montant_total: v.montant_total || computeTotal(v.lignes || []),
      statut: v.statut || "en_cours",
      date_heure_creation: v.date_heure_creation || new Date().toISOString(),
      imprimee: false,
      hash_preuve: v.hash_preuve || null,
      lignes: (v.lignes || []).map(function (l) {
        return {
          id: 0,
          produit: null,
          produit_nom: l.nom,
          quantite: l.quantite,
          prix_unitaire_snapshot: l.prix,
          sous_total: (parseFloat(l.prix) * l.quantite).toFixed(2),
        };
      }),
    };
  }

  function findVente(id) {
    const ventes = Store.getVentes();
    return ventes.find(function (v) {
      return String(v.serverId) === String(id) || String(v.id_local) === String(id);
    });
  }

  const MockAPI = {
    handle: function (path, method, body) {
      body = body || {};
      method = (method || "GET").toUpperCase();

      // POST /api/comptes/login/  (SimpleJWT : {access, refresh})
      if (path === "/comptes/login/" && method === "POST") {
        const uname = body.username || "utilisateur";
        const isSuper = /admin|super/i.test(uname);
        const role = body.role === "patron" || isSuper ? "patron" : "employe";
        const nom = uname;
        return ok({
          access: fakeJwt(role, nom),
          refresh: "mock-refresh",
          role: role,
          nom: nom,
          is_superuser: isSuper,
          nom_boutique: "Boutique " + nom,
        });
      }

      // GET /api/produits/catalogue-sync/ -> {timestamp, marchand, produits:[...]}
      if (path === "/produits/catalogue-sync/" && method === "GET") {
        return ok({
          timestamp: new Date().toISOString(),
          marchand: "Boutique " + (Store.getNom() || ""),
          produits: ensureCatalogue(),
        });
      }

      // GET /api/produits/<id>/qr/ et /barcode/ -> code-barres (compat)
      let m = path.match(/^\/produits\/([^/]+)\/(qr|barcode|code-barre)\/$/);
      if (m && method === "GET") {
        const cat = ensureCatalogue();
        const prod = cat.find(function(x){ return String(x.id)===String(m[1]); });
        const code = prod ? (prod.code_barre || prod.id_qr) : m[1];
        return ok({ produit_id: m[1], id_qr: code, code_barre: code, barcode_value: code, barcode_base64_png: null, qr_base64_png: null });
      }

      // POST /api/produits/creer/
      if (path === "/produits/creer/" && method === "POST") {
        const code = body.code_barre || body.id_qr || (""+Date.now()).padEnd(13,'0').slice(0,13);
        const suivre = !!body.suivre_stock;
        const produit = {
          id: Date.now(),
          id_qr: code,
          code_barre: code,
          nom: body.nom,
          prix: String(body.prix),
          reference: "",
          reference_nom: "",
          quantite_stock: suivre ? (body.quantite_stock == null ? 0 : body.quantite_stock) : null,
          suivre_stock: suivre,
          seuil_alerte: suivre ? (body.seuil_alerte == null ? null : body.seuil_alerte) : null,
          actif: true,
        };
        const cat = ensureCatalogue();
        cat.push(produit);
        Store.setCatalogue(cat);
        Store.addProduitLocal(produit);
        return ok(produit, 201);
      }

      // PATCH /api/produits/<id>/  (mise a jour des champs de stock)
      m = path.match(/^\/produits\/([^/]+)\/$/);
      if (m && method === "PATCH") {
        const cat = ensureCatalogue();
        const p = cat.find(function (x) {
          return String(x.id) === String(m[1]);
        });
        if (!p) return ok({ error: "Produit introuvable" }, 404);
        if (body.suivre_stock !== undefined) p.suivre_stock = !!body.suivre_stock;
        if (body.quantite_stock !== undefined) {
          p.quantite_stock = p.suivre_stock ? body.quantite_stock : null;
        }
        if (body.seuil_alerte !== undefined) {
          p.seuil_alerte = p.suivre_stock ? body.seuil_alerte : null;
        }
        if (body.nom !== undefined) p.nom = body.nom;
        if (body.prix !== undefined) p.prix = String(body.prix);
        if (body.code_barre !== undefined) p.code_barre = body.code_barre;
        if (body.id_qr !== undefined) { p.id_qr = body.id_qr; if (!p.code_barre) p.code_barre = body.id_qr; }
        Store.setCatalogue(cat);
        return ok(p);
      }
      // DELETE /api/produits/<id>/  (suppression)
      m = path.match(/^\/produits\/([^/]+)\/$/);
      if (m && method === "DELETE") {
        let cat = ensureCatalogue();
        const idx = cat.findIndex(function(x){ return String(x.id)===String(m[1]); });
        if (idx===-1) return ok({ error: "Produit introuvable" }, 404);
        cat.splice(idx,1);
        Store.setCatalogue(cat);
        return ok(null, 204);
      }

      // GET /api/produits/alertes-stock/
      if (path === "/produits/alertes-stock/" && method === "GET") {
        const cat = ensureCatalogue();
        const alertes = [];
        cat.forEach(function (p) {
          if (!p.suivre_stock) return;
          const stock = p.quantite_stock == null ? null : Number(p.quantite_stock);
          let urgence = null;
          if (stock !== null && stock <= 0) urgence = "rupture";
          else if (stock !== null && p.seuil_alerte !== null && stock <= Number(p.seuil_alerte))
            urgence = "seuil";
          if (urgence) {
            alertes.push({
              id: p.id,
              id_qr: p.id_qr,
              nom: p.nom,
              quantite_stock: p.quantite_stock,
              seuil_alerte: p.seuil_alerte,
              urgence: urgence,
            });
          }
        });
        return ok(alertes);
      }

      // GET /api/produits/tous/  (vue patron / superuser)
      if (path === "/produits/tous/" && method === "GET") {
        const cat = ensureCatalogue();
        const nom = Store.getNom();
        const out = cat.map(function (p) {
          return {
            id: p.id,
            id_qr: p.id_qr,
            code_barre: p.code_barre || p.id_qr,
            nom: p.nom,
            prix: p.prix,
            cree_par_username: nom,
            cree_par_nom: nom,
            marchand_nom: "Boutique " + nom,
          };
        });
        return ok(out);
      }

      // POST /api/ventes/  (creer une vente en cours)
      if (path === "/ventes/" && method === "POST") {
        const v = {
          id_local: uuid(),
          serverId: String(Date.now()),
          statut: "en_cours",
          lignes: [],
          pending: false,
          montant_total: "0.00",
          createur_nom: Store.getNom(),
          createur_role: Store.getRole(),
          date_heure_creation: new Date().toISOString(),
        };
        Store.saveVente(v);
        return ok(venteOut(v), 201);
      }

      // GET /api/ventes/  (historique)
      if (path === "/ventes/" && method === "GET") {
        const role = Store.getRole();
        const nom = Store.getNom();
        let list = Store.getVentes();
        if (role !== "patron") {
          list = list.filter(function (v) {
            return (v.createur_nom || "") === nom;
          });
        }
        const out = list.map(venteOut);
        return ok(out);
      }

      // POST /api/ventes/<id>/lignes/
      m = path.match(/^\/ventes\/([^/]+)\/lignes\/$/);
      if (m && method === "POST") {
        const v = findVente(m[1]);
        if (!v) return ok({ error: "Vente introuvable" }, 404);
        const code = body.code_barre || body.barcode || body.id_qr;
        const produit = Store.findInCatalogue(code);
        if (!produit) return ok({ error: "Produit inconnu: " + code }, 404);
        const qte = parseInt(body.quantite, 10) || 1;
        const exist = v.lignes.find(function (l) {
          return (l.code_barre || l.id_qr) === (produit.code_barre || produit.id_qr);
        });
        if (exist) exist.quantite += qte;
        else
          v.lignes.push({
            id_qr: produit.id_qr,
            code_barre: produit.code_barre || produit.id_qr,
            nom: produit.nom,
            prix: produit.prix,
            quantite: qte,
          });
        v.montant_total = computeTotal(v.lignes);
        Store.saveVente(v);
        const ligne = v.lignes[v.lignes.length - 1];
        return ok(
          {
            id: 0,
            produit: produit.id || null,
            produit_nom: ligne.nom,
            quantite: ligne.quantite,
            prix_unitaire_snapshot: ligne.prix,
            sous_total: (parseFloat(ligne.prix) * ligne.quantite).toFixed(2),
          },
          201
        );
      }

      // POST /api/ventes/<id>/finaliser/
      m = path.match(/^\/ventes\/([^/]+)\/finaliser\/$/);
      if (m && method === "POST") {
        const v = findVente(m[1]);
        if (!v) return ok({ error: "Vente introuvable" }, 404);
        v.statut = "finalisee";
        v.montant_total = computeTotal(v.lignes);
        v.hash_preuve = randomHash();
        v.id_unique = v.id_unique || uuid();
        Store.saveVente(v);
        return ok(venteOut(v));
      }

      // POST /api/ventes/<id>/annuler/
      m = path.match(/^\/ventes\/([^/]+)\/annuler\/$/);
      if (m && method === "POST") {
        const v = findVente(m[1]);
        if (!v) return ok({ error: "Vente introuvable" }, 404);
        v.statut = "annulee";
        Store.saveVente(v);
        return ok(venteOut(v));
      }

      // POST /api/ventes/sync/  (lot hors-ligne)
      if (path === "/ventes/sync/" && method === "POST") {
        let lot = body;
        if (lot && typeof lot === "object" && Array.isArray(lot.ventes)) lot = lot.ventes;
        lot = Array.isArray(lot) ? lot : [];
        const resultats = lot.map(function (item) {
          return {
            id_local: item.id_local,
            id_unique: uuid(),
            statut: "finalisee",
            montant_total: computeTotal(item.lignes || []),
            hash_preuve: randomHash(),
          };
        });
        return ok({ resultats: resultats, doublons_ignores: 0 });
      }

      return ok({ error: "Endpoint mock non implemente: " + method + " " + path }, 404);
    },
  };

  window.MockAPI = MockAPI;
})();
