from django.urls import path

from ventes import views

urlpatterns = [
    path("ventes/", views.VenteListeView.as_view()),
    path("ventes/sync/", views.VenteSyncView.as_view()),
    path("ventes/<int:vente_id>/lignes/", views.LigneVenteView.as_view()),
    path("ventes/<int:vente_id>/finaliser/", views.FinaliserVenteView.as_view()),
    path("ventes/<int:vente_id>/annuler/", views.AnnulerVenteView.as_view()),
    path("ventes/<int:vente_id>/ticket-escpos/", views.TicketEscPosView.as_view()),
]
