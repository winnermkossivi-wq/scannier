from django.apps import AppConfig
from django.contrib import admin


class AdministrationConfig(AppConfig):
    name = "administration"
    verbose_name = "Administration centrale"

    def ready(self):
        # Personnalisation de l'en-tete de l'admin pour le superuser
        # (proprietaire de la plateforme). Ne touche pas aux modeles des
        # autres apps : on parametre uniquement la presentation centrale.
        site = admin.site
        site.site_header = "Scannier - Administration centrale"
        site.site_title = "Scannier"
        site.index_title = "Controle de la plateforme"
        site.empty_value_display = "-"
