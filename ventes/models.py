import hashlib
import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum

from comptes.models import Employe, Marchand
from produits.models import Produit


class Vente(models.Model):
    STATUT_CHOICES = [
        ("en_cours", "En cours"),
        ("finalisee", "Finalisée"),
        ("annulee", "Annulée"),
    ]

    marchand = models.ForeignKey(
        Marchand, on_delete=models.CASCADE, related_name="ventes"
    )
    employe = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventes_employe",
    )
    id_unique = models.UUIDField(
        unique=True, db_index=True, editable=False, default=uuid.uuid4
    )
    montant_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="en_cours"
    )
    date_heure_creation = models.DateTimeField(auto_now_add=True)
    imprimee = models.BooleanField(default=False)
    hash_preuve = models.CharField(max_length=64, blank=True)
    id_local = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Identifiant local genere par le client pour la synchronisation offline.",
    )
    version_catalogue = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Version du catalogue global connue par le client (pour detecter les mises a jour).",
    )

    class Meta:
        ordering = ["-date_heure_creation"]
        constraints = [
            models.CheckConstraint(
                condition=Q(montant_total__gte=0),
                name="vente_montant_total_positif",
            ),
        ]

    def __str__(self):
        return f"Vente {self.id_unique} - {self.montant_total}"

    def calculer_hash_preuve(self):
        """SHA-256 de (id_unique + montant_total + date_creation + id_marchand)."""
        payload = "{}|{}|{}|{}".format(
            self.id_unique,
            self.montant_total,
            self.date_heure_creation,
            self.marchand_id,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def recalculer_montant_total(self):
        total = self.lignes.aggregate(total=Sum("sous_total"))["total"]
        total = total or Decimal("0")
        if self.montant_total != total:
            self.montant_total = total
            self.save(update_fields=["montant_total"])
        return self.montant_total


class LigneVente(models.Model):
    vente = models.ForeignKey(
        Vente, on_delete=models.CASCADE, related_name="lignes"
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.PROTECT, related_name="lignes_vente"
    )
    quantite = models.IntegerField()
    prix_unitaire_snapshot = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True
    )
    sous_total = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantite__gt=0),
                name="ligne_vente_quantite_positive",
            ),
        ]

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom}"

    def save(self, *args, **kwargs):
        if self.prix_unitaire_snapshot is None and self.produit_id:
            self.prix_unitaire_snapshot = self.produit.prix
        self.sous_total = Decimal(self.quantite) * self.prix_unitaire_snapshot
        super().save(*args, **kwargs)
        self.vente.recalculer_montant_total()

    def delete(self, *args, **kwargs):
        vente = self.vente
        super().delete(*args, **kwargs)
        vente.recalculer_montant_total()
