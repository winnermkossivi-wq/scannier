from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Marchand(models.Model):
    STATUT_ABONNEMENT_CHOICES = [
        ("essai", "Essai"),
        ("actif", "Actif"),
        ("expire", "Expiré"),
        ("suspendu", "Suspendu"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="marchand"
    )
    nom_boutique = models.CharField(max_length=200)
    telephone = models.CharField(max_length=30, blank=True)
    zone = models.CharField(max_length=200, blank=True)
    actif = models.BooleanField(
        default=True,
        help_text="Compte actif (False = suspendu par l'administrateur plateforme).",
    )
    raison_suspension = models.CharField(max_length=300, blank=True)
    date_suspension = models.DateTimeField(null=True, blank=True)
    statut_abonnement = models.CharField(
        max_length=10,
        choices=STATUT_ABONNEMENT_CHOICES,
        default="essai",
        help_text="Statut de l'abonnement du marchand.",
    )
    date_echeance_abonnement = models.DateField(
        null=True,
        blank=True,
        help_text="Date d'echeance de l'abonnement.",
    )

    def __str__(self):
        etat = "actif" if self.actif else "suspendu"
        return f"{self.nom_boutique} ({self.user.username}) - {etat} - {self.get_statut_abonnement_display()}"

    def suspendre(self, raison=""):
        from django.utils import timezone

        self.actif = False
        self.raison_suspension = raison
        self.date_suspension = timezone.now()
        self.save(update_fields=["actif", "raison_suspension", "date_suspension"])

    def reactiver(self):
        self.actif = True
        self.raison_suspension = ""
        self.date_suspension = None
        self.save(update_fields=["actif", "raison_suspension", "date_suspension"])

    def est_abonnement_valide(self):
        """Verifie si l'abonnement permet l'acces a l'application."""
        if self.statut_abonnement in ("expire", "suspendu"):
            return False
        if self.statut_abonnement == "actif" and self.date_echeance_abonnement:
            from django.utils import timezone
            if timezone.now().date() > self.date_echeance_abonnement:
                return False
        return True


class Employe(models.Model):
    ROLE_CHOICES = [
        ("patron", "Patron"),
        ("employe", "Employé"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employe"
    )
    marchand = models.ForeignKey(
        Marchand, on_delete=models.CASCADE, related_name="employes"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="employe")
    actif = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["marchand", "user"], name="unique_employe_par_marchand"
            ),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.marchand.nom_boutique}"

    def suspendre(self):
        """Suspend un employe precise sans suspendre tout le marchand."""
        self.actif = False
        self.save(update_fields=["actif"])

    def reactiver(self):
        self.actif = True
        self.save(update_fields=["actif"])


@receiver(post_save, sender=Marchand)
def creer_patron_employe(sender, instance, created, **kwargs):
    """A l'inscription d'un Marchand, un Employe 'patron' est cree automatiquement."""
    if created:
        Employe.objects.get_or_create(
            user=instance.user,
            marchand=instance,
            defaults={"role": "patron", "actif": True},
        )
