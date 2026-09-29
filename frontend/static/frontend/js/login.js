/* login.js */
(function () {
  const form = document.getElementById("login-form");
  const msg = document.getElementById("msg");

  function show(text, type) {
    msg.textContent = text;
    msg.className = "msg " + (type || "info");
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const role = document.getElementById("role").value;

    if (!username || !password) {
      show("Veuillez remplir tous les champs.", "error");
      return;
    }

    show("Connexion...", "info");
    try {
      const r = await Api.login(username, password, role);
      if (r.ok && r.data) {
        const token = r.data.token || (r.data.access) || null;
        const apiRole = r.data.role || role;
        const nom = r.data.nom || username;
        const isSuperuser = !!r.data.is_superuser;
        if (!token) {
          show("Réponse de connexion invalide (pas de token).", "error");
          return;
        }
        Store.setAuth(token, apiRole, nom, isSuperuser);
        await Api.syncCatalogue();
        window.location.href = "/tableau-de-bord/";
      } else {
        show("Échec de la connexion. Vérifiez vos identifiants.", "error");
      }
    } catch (err) {
      show("Erreur réseau : " + err.message, "error");
    }
  });

  // Si deja connecte, on va direct a la vente.
  if (Store.isAuthed()) {
    window.location.href = "/tableau-de-bord/";
  }
})();
