from django.contrib import admin
from django.utils import timezone
from datetime import timedelta

from .models import Employe, Marchand


@admin.register(Marchand)
class MarchandAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nom_boutique",
        "user",
        "zone",
        "actif",
        "statut_abonnement",
        "date_echeance_abonnement",
        "raison_suspension",
        "date_suspension",
    )
    list_filter = ("actif", "statut_abonnement", "zone")
    search_fields = ("nom_boutique", "telephone", "zone", "user__username")
    actions = [
        "action_suspendre",
        "action_reactiver",
        "action_abonner_1_mois",
        "action_abonner_3_mois",
        "action_abonner_12_mois",
        "action_statut_essai",
        "action_statut_expire",
        "action_statut_suspendu",
    ]

    @admin.action(description="Suspendre le(s) marchand(s) selectionne(s)")
    def action_suspendre(self, request, queryset):
        n = 0
        for m in queryset:
            if m.actif:
                m.suspendre(raison="Suspension par l'administrateur")
                n += 1
        self.message_user(request, f"{n} marchand(s) suspendu(s).")

    @admin.action(description="Reactiver le(s) marchand(s) selectionne(s)")
    def action_reactiver(self, request, queryset):
        n = 0
        for m in queryset:
            if not m.actif:
                m.reactiver()
                n += 1
        self.message_user(request, f"{n} marchand(s) reactive(s).")

    @admin.action(description="Activer abonnement 1 mois")
    def action_abonner_1_mois(self, request, queryset):
        self._mettre_a_jour_abonnement(request, queryset, mois=1, statut="actif")

    @admin.action(description="Activer abonnement 3 mois")
    def action_abonner_3_mois(self, request, queryset):
        self._mettre_a_jour_abonnement(request, queryset, mois=3, statut="actif")

    @admin.action(description="Activer abonnement 12 mois")
    def action_abonner_12_mois(self, request, queryset):
        self._mettre_a_jour_abonnement(request, queryset, mois=12, statut="actif")

    @admin.action(description="Passer en statut Essai")
    def action_statut_essai(self, request, queryset):
        n = queryset.update(statut_abonnement="essai", date_echeance_abonnement=None)
        self.message_user(request, f"{n} marchand(s) passe(s) en Essai.")

    @admin.action(description="Passer en statut Expire")
    def action_statut_expire(self, request, queryset):
        n = queryset.update(statut_abonnement="expire")
        self.message_user(request, f"{n} marchand(s) passe(s) en Expire.")

    @admin.action(description="Passer en statut Suspendu (abonn.)")
    def action_statut_suspendu(self, request, queryset):
        n = queryset.update(statut_abonnement="suspendu")
        self.message_user(request, f"{n} marchand(s) passe(s) en Suspendu.")

    def _mettre_a_jour_abonnement(self, request, queryset, mois, statut):
        aujourdhui = timezone.now().date()
        nouvelle_echeance = aujourdhui + timedelta(days=30 * mois)
        n = queryset.update(
            statut_abonnement=statut,
            date_echeance_abonnement=nouvelle_echeance,
            actif=True,
        )
        self.message_user(
            request,
            f"{n} marchand(s) abonne(s) pour {mois} mois (echeance: {nouvelle_echeance}).",
        )


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "marchand", "role", "actif")
    list_filter = ("role", "actif", "marchand")
    search_fields = ("user__username", "marchand__nom_boutique")
    actions = ["action_suspendre_employe", "action_reactiver_employe"]

    @admin.action(description="Suspendre le(s) employe(s) selectionne(s)")
    def action_suspendre_employe(self, request, queryset):
        n = 0
        for e in queryset:
            if e.actif:
                e.suspendre()
                n += 1
        self.message_user(request, f"{n} employe(s) suspendu(s).")

    @admin.action(description="Reactiver le(s) employe(s) selectionne(s)")
    def action_reactiver_employe(self, request, queryset):
        n = 0
        for e in queryset:
            if not e.actif:
                e.reactiver()
                n += 1
        self.message_user(request, f"{n} employe(s) reactive(s).")
