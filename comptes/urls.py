from django.urls import path

from . import views

app_name = "comptes"

urlpatterns = [
    path("employes/", views.EmployeListView.as_view(), name="employe-list"),
    path("employes/ajouter/", views.EmployeCreateView.as_view(), name="employe-create"),
    path("employes/stats/", views.EmployeStatsView.as_view(), name="employe-stats"),
    path("employes/<int:pk>/", views.EmployeDetailView.as_view(), name="employe-detail"),
    path("employes/<int:pk>/ventes/", views.EmployeVentesView.as_view(), name="employe-ventes"),
    path("employes/<int:pk>/toggle/", views.EmployeToggleView.as_view(), name="employe-toggle"),
    path("employes/<int:pk>/supprimer/", views.EmployeDeleteView.as_view(), name="employe-delete"),
]
