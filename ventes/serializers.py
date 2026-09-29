from rest_framework import serializers

from produits.models import Produit
from ventes.models import LigneVente, Vente


class LigneVenteSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source="produit.nom", read_only=True)

    class Meta:
        model = LigneVente
        fields = (
            "id",
            "produit",
            "produit_nom",
            "quantite",
            "prix_unitaire_snapshot",
            "sous_total",
        )


class AjoutLigneSerializer(serializers.Serializer):
    produit = serializers.IntegerField(required=False)
    quantite = serializers.IntegerField(min_value=1)
    id_qr = serializers.CharField(required=False, allow_blank=True)
    code_barre = serializers.CharField(required=False, allow_blank=True)
    barcode = serializers.CharField(required=False, allow_blank=True)


class SyncLigneSerializer(serializers.Serializer):
    """Une ligne envoyee par le client lors de la synchronisation offline."""

    id_qr = serializers.CharField(required=False, allow_blank=True)
    code_barre = serializers.CharField(required=False, allow_blank=True)
    barcode = serializers.CharField(required=False, allow_blank=True)
    produit = serializers.IntegerField(required=False)
    quantite = serializers.IntegerField(min_value=1)


class SyncVenteSerializer(serializers.Serializer):
    """Une vente hors-ligne envoyee par le client (avec ses lignes)."""

    id_local = serializers.CharField(max_length=64)
    date_heure_creation = serializers.DateTimeField(required=False)
    version_catalogue = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )
    lignes = SyncLigneSerializer(many=True)


class VenteSerializer(serializers.ModelSerializer):
    lignes = LigneVenteSerializer(many=True, read_only=True)
    marchand_nom = serializers.CharField(source="marchand.nom_boutique", read_only=True)
    employe_username = serializers.CharField(source="employe.user.username", read_only=True)

    class Meta:
        model = Vente
        fields = (
            "id",
            "id_unique",
            "marchand",
            "marchand_nom",
            "employe",
            "employe_username",
            "montant_total",
            "statut",
            "date_heure_creation",
            "imprimee",
            "hash_preuve",
            "lignes",
        )
        read_only_fields = fields


class ResultatSyncSerializer(serializers.Serializer):
    id_local = serializers.CharField()
    id_unique = serializers.CharField()
    statut = serializers.CharField()
    montant_total = serializers.CharField()
    hash_preuve = serializers.CharField()


class SyncOutSerializer(serializers.Serializer):
    resultats = ResultatSyncSerializer(many=True)
    doublons_ignores = serializers.IntegerField()


class TicketEscPosOutSerializer(serializers.Serializer):
    format = serializers.CharField()
    vente_id = serializers.IntegerField()
    id_unique = serializers.CharField()
    octets = serializers.IntegerField()
    ticket_base64 = serializers.CharField()
