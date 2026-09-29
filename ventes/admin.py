from django.contrib import admin

from .models import LigneVente, Vente


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 1


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "id_unique",
        "marchand",
        "employe",
        "montant_total",
        "statut",
        "imprimee",
        "hash_preuve",
        "date_heure_creation",
    )
    list_filter = ("statut", "imprimee", "marchand")
    search_fields = ("id_unique", "marchand__nom_boutique", "employe__user__username")
    readonly_fields = ("montant_total", "id_unique", "hash_preuve")
    date_hierarchy = "date_heure_creation"
    inlines = [LigneVenteInline]


@admin.register(LigneVente)
class LigneVenteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vente",
        "produit",
        "quantite",
        "prix_unitaire_snapshot",
        "sous_total",
    )
    search_fields = ("vente__id_unique", "produit__nom", "produit__code_barre")
