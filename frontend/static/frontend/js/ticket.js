/* ticket.js - Page "Ticket" : affiche le dernier ticket (Store) et permet
   l'impression (navigateur ou Bluetooth ESC/POS via bluetooth.js). */
(function () {
  const zone = document.getElementById("ticket-zone");
  const empty = document.getElementById("empty");

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(n) {
    return parseFloat(n || 0).toFixed(2) + " FCFA";
  }

  function render(t) {
    if (!t) {
      empty.classList.remove("hidden");
      zone.innerHTML = "";
      return;
    }
    empty.classList.add("hidden");
    const lignes = (t.lignes || [])
      .map(function (l) {
        return (
          '<div class="t-row"><span>' +
          escapeHtml(l.nom) +
          " x" +
          l.quantite +
          "</span><span>" +
          fmt(parseFloat(l.prix) * l.quantite) +
          "</span></div>"
        );
      })
      .join("");
    zone.innerHTML =
      '<div class="ticket">' +
      '<div class="t-header">SCANNIER</div>' +
      '<div class="t-sub">Merci pour votre achat</div>' +
      lignes +
      '<div class="t-total"><span>TOTAL</span><span>' +
      fmt(t.total) +
      "</span></div>" +
      '<div class="t-meta">ID: ' +
      escapeHtml(t.id_unique) +
      "</div>" +
      '<div class="t-meta">Preuve: ' +
      escapeHtml(t.hash_preuve) +
      "</div>" +
      (t.date_heure ? '<div class="t-meta">' + escapeHtml(t.date_heure) + "</div>" : "") +
      "</div>";
  }

  const bt = document.getElementById("bt-print");
  if (bt)
    bt.addEventListener("click", async function () {
      const t = Store.getLastTicket();
      if (!t) return;
      bt.disabled = true;
      bt.textContent = "Impression…";
      const r = await window.BluetoothPrinter.print(t);
      bt.disabled = false;
      bt.textContent = "Imprimer (Bluetooth)";
      if (r && r.methode === "fallback")
        console.log("Bluetooth indisponible : repli impression navigateur.");
    });

  (async function init() {
    await Store.ready;
    render(Store.getLastTicket());
  })();
})();
