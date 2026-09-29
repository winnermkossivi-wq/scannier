/* app.js - UI commune : barre de navigation, badge role, deconnexion, menu mobile. */
(function () {
  function initChrome() {
    const nav = document.getElementById("nav");
    const badge = document.getElementById("role-badge");
    const logout = document.getElementById("logout-link");

    // Mobile menu elements
    const mobileAuthed = document.getElementById("mobile-menu-authed");
    const mobileUnauthed = document.getElementById("mobile-menu-unauthed");
    const mobileEmployes = document.getElementById("mobile-menu-employes");
    const mobileEmployesDisabled = document.getElementById("mobile-menu-employes-disabled");

    if (Store.isAuthed()) {
      if (nav) nav.classList.remove("hidden");
      const role = Store.getRole();
      const nom = Store.getNom();
      if (badge) {
        badge.textContent = (role === "patron" ? "Patron" : "Employé") + (nom ? " · " + nom : "");
        badge.className = "badge badge-sm";
        if (role === "patron") {
          badge.style.background = "#dbeafe";
          badge.style.color = "#2563eb";
        } else {
          badge.style.background = "#f3e8ff";
          badge.style.color = "#7c3aed";
        }
      }
      // "Tous les produits" : reserve au patron ou au superuser.
      const navTous = document.getElementById("nav-tous");
      if (navTous && Store.isPatronOrSuper()) navTous.classList.remove("hidden");

      // Mobile menu: show authed, hide unauthed
      if (mobileAuthed) mobileAuthed.classList.remove("hidden");
      if (mobileUnauthed) mobileUnauthed.classList.add("hidden");
      // Employés link: only for patron
      if (role === "patron") {
        if (mobileEmployes) mobileEmployes.classList.remove("hidden");
        if (mobileEmployesDisabled) mobileEmployesDisabled.classList.add("hidden");
      } else {
        if (mobileEmployes) mobileEmployes.classList.add("hidden");
        if (mobileEmployesDisabled) mobileEmployesDisabled.classList.remove("hidden");
      }
    } else {
      if (nav) nav.classList.add("hidden");
      if (badge) {
        badge.classList.add("hidden");
        badge.style.background = "";
        badge.style.color = "";
      }
      // Mobile menu: show unauthed, hide authed
      if (mobileAuthed) mobileAuthed.classList.add("hidden");
      if (mobileUnauthed) mobileUnauthed.classList.remove("hidden");
    }

    if (logout) {
      logout.addEventListener("click", function (e) {
        e.preventDefault();
        Store.clearAuth();
        window.location.href = "/connexion/";
      });
    }

    // Petit bandeau indiquant le mode simulation.
    if (window.USE_MOCK) {
      const div = document.createElement("div");
      div.id = "modeswitch";
      div.className = "no-print";
      div.textContent = "Mode simulation actif (API non connectée). Données fictives.";
      document.body.appendChild(div);
    }
  }

  document.addEventListener("DOMContentLoaded", initChrome);
})();
