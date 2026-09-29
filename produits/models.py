import random
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from comptes.models import Marchand


def _generer_code_barre():
    """Genere un EAN-13 valide (12 chiffres + checksum) pour Code128/EAN."""
    base = "".join(str(random.randint(0, 9)) for _ in range(12))
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
    check = (10 - total % 10) % 10
    return base + str(check)


class ProduitReference(models.Model):
    """Catalogue global de produits (sans prix), modifiable uniquement par un superuser."""

    nom = models.CharField(max_length=200)
    categorie = models.CharField(max_length=100, blank=True)
    version = models.CharField(
        max_length=30, default="v1.0", help_text="Version du catalogue pour le sync offline."
    )

    class Meta:
        ordering = ["categorie", "nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["nom", "categorie"], name="unique_reference_nom_categorie"
            ),
        ]

    def __str__(self):
        if self.categorie:
            return f"{self.nom} ({self.categorie})"
        return self.nom


class Produit(models.Model):
    marchand = models.ForeignKey(
        Marchand, on_delete=models.CASCADE, related_name="produits"
    )
    reference = models.ForeignKey(
        ProduitReference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produits",
    )
    nom = models.CharField(max_length=200)
    id_qr = models.UUIDField(
        unique=True, db_index=True, editable=False, default=uuid.uuid4
    )
    code_barre = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        blank=True,
        default=_generer_code_barre,
        help_text="Code-barres EAN-13 / Code128 (genere automatiquement, scannable).",
    )
    prix = models.DecimalField(max_digits=12, decimal_places=2)
    quantite_stock = models.IntegerField(null=True, blank=True)
    suivre_stock = models.BooleanField(
        default=False, help_text="Suivre le stock de ce produit."
    )
    seuil_alerte = models.IntegerField(
        null=True, blank=True, help_text="Seuil d'alerte (stock bas)."
    )
    en_rupture = models.BooleanField(
        default=False,
        help_text="Indicateur de rupture de stock (quantite_stock <= 0).",
    )
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(
        "comptes.Employe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produits_crees",
        help_text="Employe ayant cree le produit (en plus du marchand).",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(prix__gt=0), name="produit_prix_positif"
            ),
            models.CheckConstraint(
                condition=Q(quantite_stock__gte=0) | Q(quantite_stock__isnull=True),
                name="produit_stock_positif",
            ),
        ]
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.id_qr})"

    def save(self, *args, **kwargs):
        if self.reference_id and not self.nom:
            self.nom = self.reference.nom
        if not self.code_barre:
            self.code_barre = _generer_code_barre()
        super().save(*args, **kwargs)

    @property
    def barcode_value(self):
        """Valeur a encoder dans le code-barres (priorite code_barre)."""
        return self.code_barre or str(self.id_qr).replace("-", "")
