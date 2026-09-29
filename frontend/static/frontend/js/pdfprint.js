/* pdfprint.js - Impression d'etiquettes QR au format PDF via l'API, avec
   repli sur une etiquette HTML imprimable si l'endpoint n'est pas disponible
   (mode simulation / hors-ligne). */
(function () {
  function downloadBlob(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
    }, 60000);
  }

  /* Tente l'endpoint /api/produits/<id>/qrcode-pdf/?quantite=N.
     Retourne true si le PDF a pu etre ouvert, false sinon (le appelant
     peut alors replier sur une etiquette HTML). */
  async function imprimerProduitPDF(produit, quantite) {
    quantite = Math.max(1, Math.min(parseInt(quantite, 10) || 1, 100));
    if (!produit || !produit.id) return false;

    const url =
      window.API_BASE + "/produits/" + produit.id + "/qrcode-pdf/?quantite=" + quantite;
    const headers = {};
    const token = Store.getToken();
    if (token) headers["Authorization"] = "Bearer " + token;

    try {
      const r = await fetch(url, { headers: headers });
      if (r.ok) {
        const blob = await r.blob();
        const objUrl = URL.createObjectURL(blob);
        const w = window.open(objUrl, "_blank");
        if (!w) {
          // Bloqueur de pop-up : on propose un telechargement a la place.
          downloadBlob(blob, "etiquettes_" + produit.id + ".pdf");
        }
        setTimeout(function () {
          URL.revokeObjectURL(objUrl);
        }, 60000);
        return true;
      }
    } catch (e) {
      /* pas de serveur / endpoint : on laisse le repli s'en charger */
    }
    return false;
  }

  window.imprimerProduitPDF = imprimerProduitPDF;
})();
