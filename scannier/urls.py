"""
URL configuration for scannier project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from administration import views as administration_views
from comptes.views import LoginView
from frontend import urls as frontend_urls

urlpatterns = [
    path("api/health/", administration_views.health_check, name="health"),
    path("api/support/signaler-bug/", administration_views.signaler_bug, name="signaler_bug"),
    path("api/comptes/login/", LoginView.as_view(), name="api_login"),
    path("api/comptes/", include("comptes.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/", include("produits.urls")),
    path("api/", include("ventes.urls")),
    path(
        "admin/statistiques/",
        administration_views.statistiques_globales,
        name="admin-statistiques",
    ),
    path("admin/", admin.site.urls),
    path("", include("frontend.urls", namespace="frontend")),
]
