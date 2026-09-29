"""Vues de l'application frontend.

Elles ne font qu'afficher des templates HTML. Tout l'appel a l'API (et le
mode simulation est gere cote navigateur dans les fichiers static/.
"""
from django.conf import settings
from django.shortcuts import redirect, render


def _ctx(request):
    return {
        "USE_MOCK": getattr(settings, "FRONTEND_USE_MOCK", True),
        "API_BASE": getattr(settings, "API_BASE", "/api"),
    }


def login_page(request):
    return render(request, "frontend/login.html", _ctx(request))


def register_page(request):
    ctx = _ctx(request)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        nom_boutique = request.POST.get("nom_boutique", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        if not username or not nom_boutique or not password:
            ctx["error"] = "Veuillez remplir tous les champs obligatoires."
            return render(request, "frontend/register.html", ctx)
        if password != password2:
            ctx["error"] = "Les mots de passe ne correspondent pas."
            return render(request, "frontend/register.html", ctx)
        if User.objects.filter(username=username).exists():
            ctx["error"] = "Ce nom d'utilisateur existe déjà."
            return render(request, "frontend/register.html", ctx)
        if len(password) < 6:
            ctx["error"] = "Le mot de passe doit contenir au moins 6 caractères."
            return render(request, "frontend/register.html", ctx)

        user = User.objects.create_user(username=username, password=password)
        Marchand.objects.create(user=user, nom_boutique=nom_boutique)
        return redirect("frontend:login")

    return render(request, "frontend/register.html", ctx)

    # GET sur l'ancienne page -> redirige vers login avec onglet Sign up
    return redirect("frontend:login")


def nouvelle_vente(request):
    return render(request, "frontend/nouvelle_vente.html", _ctx(request))


def ticket(request):
    return render(request, "frontend/ticket.html", _ctx(request))


def produits(request):
    return render(request, "frontend/produits.html", _ctx(request))


def tableau_de_bord(request):
    return render(request, "frontend/dashboard.html", _ctx(request))


def tous_produits(request):
    return render(request, "frontend/tous_produits.html", _ctx(request))


def historique(request):
    return render(request, "frontend/historique.html", _ctx(request))


def employes(request):
    return render(request, "frontend/employes.html", _ctx(request))


def deconnexion(request):
    return redirect("frontend:login")


def confidentialite(request):
    return render(request, "frontend/confidentialite.html", _ctx(request))
