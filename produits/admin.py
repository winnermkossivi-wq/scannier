from django.contrib import admin

from .models import Produit, ProduitReference

SEUIL_PRIX_SUSPECT = 100  # FCFA : seuil heuristique pour detecter des prix anormalement bas


class PrixSuspectFilter(admin.SimpleListFilter):
    title = "prix suspects"
    parameter_name = "prix_suspect"

    def lookups(self, request, model_admin):
        return (
            ("bas", "Prix <= %d FCFA" % SEUIL_PRIX_SUSPECT),
            ("tous", "Tous"),
        )

    def queryset(self, request, queryset):
        if self.value() == "bas":
            return queryset.filter(prix__lte=SEUIL_PRIX_SUSPECT)
        return queryset


@admin.register(ProduitReference)
class ProduitReferenceAdmin(admin.ModelAdmin):
    """Catalogue global : uniquement un superuser peut modifier ces donnees."""

    list_display = ("id", "nom", "categorie")
    list_filter = ("categorie",)
    search_fields = ("nom", "categorie")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    """Vue superuser : createur (employe) + boutique d'origine par produit.

    Facilite la detection de fraude (employe creant un prix anormalement bas)
    via la colonne 'Prix suspect' et le filtre associe.
    """

    list_display = (
        "id",
        "nom",
        "id_qr",
        "reference",
        "prix",
        "quantite_stock",
        "actif",
        "cree_par",
        "marchand",
        "date_creation",
        "prix_anormalement_bas",
    )
    list_filter = ("actif", "marchand", "cree_par", PrixSuspectFilter)
    search_fields = ("nom", "id_qr", "marchand__nom_boutique", "cree_par__user__username")

    @admin.display(boolean=True, description="Prix suspect")
    def prix_anormalement_bas(self, obj):
        return obj.prix is not None and obj.prix <= SEUIL_PRIX_SUSPECT
