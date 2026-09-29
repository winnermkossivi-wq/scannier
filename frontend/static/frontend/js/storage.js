/* storage.js - Persistance cote navigateur avec IndexedDB.
   - Le catalogue produit et les ventes en attente de synchro sont stockes
     dans IndexedDB (plus robuste que localStorage pour ce volume).
   - Un cache memoire miroir permet de garder l'API synchrone utilisee par le
     reste du code ; les ecritures sont repliquees dans IndexedDB.
   - L'authentification (token/role/nom) reste en localStorage (leger,
     propre au compte). */
(function () {
  const DB_NAME = "scannier";
  const DB_VERSION = 1;
  const K = {
    TOKEN: "scannier_token",
    ROLE: "scannier_role",
    NOM: "scannier_nom",
    SUPER: "scannier_super",
  };

  let db = null;
  const cache = {
    catalogue: null,
    ventes: [],
    produitsLocaux: [],
    lastTicket: null,
  };

  function openDB() {
    return new Promise(function (resolve, reject) {
      if (!("indexedDB" in window)) {
        reject(new Error("IndexedDB indisponible"));
        return;
      }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function (e) {
        const d = e.target.result;
        if (!d.objectStoreNames.contains("catalogue"))
          d.createObjectStore("catalogue", { keyPath: "k" });
        if (!d.objectStoreNames.contains("ventes"))
          d.createObjectStore("ventes", { keyPath: "id_local" });
        if (!d.objectStoreNames.contains("kv"))
          d.createObjectStore("kv", { keyPath: "k" });
      };
      req.onsuccess = function () {
        db = req.result;
        resolve(db);
      };
      req.onerror = function () {
        reject(req.error);
      };
    });
  }

  function tx(store, mode) {
    return db.transaction(store, mode).objectStore(store);
  }
  function reqToPromise(request) {
    return new Promise(function (resolve, reject) {
      request.onsuccess = function () {
        resolve(request.result);
      };
      request.onerror = function () {
        reject(request.error);
      };
    });
  }

  function hydrate() {
    const prom = Promise.all([
      reqToPromise(tx("catalogue", "readonly").get("current")).then(function (r) {
        cache.catalogue = r ? r.data : null;
      }),
      reqToPromise(tx("ventes", "readonly").getAll()).then(function (r) {
        cache.ventes = Array.isArray(r) ? r : [];
      }),
      reqToPromise(tx("kv", "readonly").get("produits_locaux")).then(function (r) {
        cache.produitsLocaux = r ? r.data : [];
      }),
      reqToPromise(tx("kv", "readonly").get("lastTicket")).then(function (r) {
        cache.lastTicket = r ? r.data : null;
      }),
    ]);
    return prom;
  }

  // Initialisation (ouverte + hydratation). Stocke la promesse dans Store.ready.
  let readyPromise = null;
  function init() {
    if (readyPromise) return readyPromise;
    readyPromise = openDB()
      .then(hydrate)
      .catch(function (e) {
        // IndexedDB indisponible (navigation privee par ex.) : on continue
        // sans persistances hors-ligne.
        console.warn("Stockage hors-ligne indisponible :", e.message);
      });
    return readyPromise;
  }

  function b64urlDecode(str) {
    if (!str || str.split(".").length !== 3) return null;
    try {
      const p = str.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      return JSON.parse(
        decodeURIComponent(
          atob(p)
            .split("")
            .map(function (c) {
              return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
            })
            .join("")
        )
      );
    } catch (e) {
      return null;
    }
  }

  const Store = {
    ready: init(),

    // --- Authentification (localStorage) ---
    setAuth: function (token, role, nom, isSuperuser) {
      localStorage.setItem(K.TOKEN, token);
      if (role) localStorage.setItem(K.ROLE, role);
      if (nom) localStorage.setItem(K.NOM, nom);
      if (isSuperuser) localStorage.setItem(K.SUPER, "1");
      else localStorage.removeItem(K.SUPER);
    },
    getToken: function () {
      return localStorage.getItem(K.TOKEN);
    },
    getRole: function () {
      const t = localStorage.getItem(K.TOKEN);
      if (t) {
        const p = b64urlDecode(t);
        if (p && p.role) return p.role;
      }
      return localStorage.getItem(K.ROLE);
    },
    getNom: function () {
      return localStorage.getItem(K.NOM) || "";
    },
    isAuthed: function () {
      return !!localStorage.getItem(K.TOKEN);
    },
    isSuperuser: function () {
      return localStorage.getItem(K.SUPER) === "1";
    },
    isPatronOrSuper: function () {
      return this.getRole() === "patron" || this.isSuperuser();
    },
    clearAuth: function () {
      localStorage.removeItem(K.TOKEN);
      localStorage.removeItem(K.ROLE);
      localStorage.removeItem(K.NOM);
      localStorage.removeItem(K.SUPER);
    },

    // --- Catalogue (IndexedDB) ---
    getCatalogue: function () {
      return cache.catalogue;
    },
    setCatalogue: function (list) {
      cache.catalogue = list || [];
      if (db)
        reqToPromise(
          tx("catalogue", "readwrite").put({ k: "current", data: cache.catalogue })
        ).catch(function () {});
    },
    findInCatalogue: function (value) {
        const cat = cache.catalogue || [];
        return cat.find(function (p) {
          return String(p.code_barre) === String(value) || String(p.id_qr) === String(value) || String(p.barcode_value) === String(value);
        });
      },
      findByBarcode: function (value) {
        return this.findInCatalogue(value);
      },

    // --- Ventes / file d'attente hors-ligne (IndexedDB, keyPath id_local) ---
    getVentes: function () {
      return cache.ventes;
    },
    getVente: function (id_local) {
      return cache.ventes.find(function (v) {
        return v.id_local === id_local;
      });
    },
    saveVente: function (vente) {
      const i = cache.ventes.findIndex(function (v) {
        return v.id_local === vente.id_local;
      });
      if (i >= 0) cache.ventes[i] = vente;
      else cache.ventes.push(vente);
      if (db)
        reqToPromise(tx("ventes", "readwrite").put(vente)).catch(function () {});
      return vente;
    },
    getPendingVentes: function () {
      return cache.ventes.filter(function (v) {
        return v.pending;
      });
    },
    removeVente: function (id_local) {
      cache.ventes = cache.ventes.filter(function (v) {
        return v.id_local !== id_local;
      });
      if (db)
        reqToPromise(tx("ventes", "readwrite").delete(id_local)).catch(function () {});
    },

    // --- Produits locaux (ajouts hors-ligne) ---
    getProduitsLocaux: function () {
      return cache.produitsLocaux;
    },
    addProduitLocal: function (p) {
      cache.produitsLocaux.push(p);
      if (db)
        reqToPromise(
          tx("kv", "readwrite").put({
            k: "produits_locaux",
            data: cache.produitsLocaux,
          })
        ).catch(function () {});
    },

    // --- Dernier ticket ---
    getLastTicket: function () {
      return cache.lastTicket;
    },
    setLastTicket: function (t) {
      cache.lastTicket = t;
      if (db)
        reqToPromise(tx("kv", "readwrite").put({ k: "lastTicket", data: t })).catch(
          function () {}
        );
    },
  };

  window.Store = Store;
})();
