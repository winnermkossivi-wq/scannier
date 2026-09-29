"""
URLs de l'application frontend (pages HTML du projet Scannier).
Toutes les pages sont servies par des vues simples qui rendent un template.
La logique métier / les appels API sont cotes navigateur (static JS).
"""
from django.urls import path

from . import views

app_name = "frontend"

urlpatterns = [
    path("", views.login_page, name="accueil"),
    path("connexion/", views.login_page, name="login_redirect"),
    path("login/", views.login_page, name="login"),
    path("inscription/", views.register_page, name="register"),
    path("register/", views.register_page, name="register_alias"),
    path("tableau-de-bord/", views.tableau_de_bord, name="tableau_de_bord"),
    path("vente/nouvelle/", views.nouvelle_vente, name="nouvelle_vente"),
    path("vente/ticket/", views.ticket, name="ticket"),
    path("produits/", views.produits, name="produits"),
    path("produits/tous/", views.tous_produits, name="tous_produits"),
    path("employes/", views.employes, name="employes"),
    path("historique/", views.historique, name="historique"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("confidentialite/", views.confidentialite, name="confidentialite"),
]
