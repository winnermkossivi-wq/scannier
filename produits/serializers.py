import unicodedata
from rest_framework import serializers

from produits.models import Produit


def valider_ean13(code: str) -> bool:
    """Valide un code EAN-13 : 13 chiffres + checksum correct."""
    if not code or len(code) != 13 or not code.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(code[:12]))
    check = (10 - total % 10) % 10
    return check == int(code[12])


def normaliser_nom(nom: str) -> str:
    """Normalise un nom pour comparaison : minuscules, sans accents, espaces reduits."""
    if not nom:
        return ""
    nom = unicodedata.normalize("NFD", nom)
    nom = "".join(c for c in nom if unicodedata.category(c) != "Mn")
    return " ".join(nom.lower().split())


class ProduitCatalogueSerializer(serializers.ModelSerializer):
    reference_nom = serializers.CharField(source="reference.nom", read_only=True)
    en_rupture = serializers.BooleanField(read_only=True)

    class Meta:
        model = Produit
        fields = (
            "id",
            "id_qr",
            "code_barre",
            "nom",
            "prix",
            "reference",
            "reference_nom",
            "quantite_stock",
            "suivre_stock",
            "seuil_alerte",
            "en_rupture",
            "actif",
            "date_modification",
        )


class ProduitCatalogueSyncSerializer(serializers.ModelSerializer):
    """Catalogue pour synchronisation incrementale (avec date de modification)."""

    reference_nom = serializers.CharField(source="reference.nom", read_only=True)
    en_rupture = serializers.BooleanField(read_only=True)

    class Meta:
        model = Produit
        fields = (
            "id",
            "id_qr",
            "code_barre",
            "nom",
            "prix",
            "reference",
            "reference_nom",
            "quantite_stock",
            "suivre_stock",
            "seuil_alerte",
            "en_rupture",
            "actif",
            "date_modification",
        )


class ProduitCreateSerializer(serializers.ModelSerializer):
    """Creation d'un produit (le marchand et le createur sont imposes cote serveur)."""

    code_barre = serializers.CharField(required=False, allow_blank=True, max_length=64)
    suggestions_doublons = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Produit
        fields = (
            "nom",
            "prix",
            "code_barre",
            "quantite_stock",
            "suivre_stock",
            "seuil_alerte",
            "reference",
            "actif",
            "suggestions_doublons",
        )

    def validate_prix(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Le prix doit etre strictement positif.")
        return value

    def validate_quantite_stock(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Le stock ne peut pas etre negatif.")
        return value

    def validate_seuil_alerte(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Le seuil d'alerte ne peut pas etre negatif.")
        return value

    def validate_nom(self, value):
        if not str(value).strip():
            raise serializers.ValidationError("Le nom du produit est obligatoire.")
        return value.strip()

    def validate_code_barre(self, value):
        if value and not valider_ean13(value):
            raise serializers.ValidationError(
                "Code-barres invalide : doit etre un EAN-13 (13 chiffres avec checksum correct)."
            )
        return value

    def get_suggestions_doublons(self, obj):
        return getattr(obj, "suggestions_doublons", None)


class ProduitUpdateSerializer(serializers.ModelSerializer):
    """Mise a jour (partielle) d'un produit, centree sur le suivi de stock."""

    class Meta:
        model = Produit
        fields = (
            "nom",
            "prix",
            "code_barre",
            "quantite_stock",
            "suivre_stock",
            "seuil_alerte",
            "actif",
            "reference",
        )

    def validate_quantite_stock(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Le stock ne peut pas etre negatif.")
        return value

    def validate_seuil_alerte(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Le seuil d'alerte ne peut pas etre negatif.")
        return value

    def validate_nom(self, value):
        if not str(value).strip():
            raise serializers.ValidationError("Le nom du produit est obligatoire.")
        return value.strip()

    def validate_code_barre(self, value):
        if value and not valider_ean13(value):
            raise serializers.ValidationError(
                "Code-barres invalide : doit etre un EAN-13 (13 chiffres avec checksum correct)."
            )
        return value


class ProduitTousSerializer(serializers.ModelSerializer):
    """Vue patrimoniale : createur (employe) + boutique d'origine."""

    cree_par_username = serializers.CharField(
        source="cree_par.user.username", read_only=True, default=None
    )
    marchand_nom = serializers.CharField(
        source="marchand.nom_boutique", read_only=True
    )
    en_rupture = serializers.BooleanField(read_only=True)

    class Meta:
        model = Produit
        fields = (
            "id",
            "id_qr",
            "code_barre",
            "nom",
            "prix",
            "quantite_stock",
            "suivre_stock",
            "seuil_alerte",
            "en_rupture",
            "actif",
            "cree_par_username",
            "marchand_nom",
        )


class ProduitQrOutSerializer(serializers.Serializer):
    produit_id = serializers.IntegerField()
    id_qr = serializers.CharField()
    qr_base64_png = serializers.CharField(required=False)
    barcode_base64_png = serializers.CharField(required=False)
    code_barre = serializers.CharField(required=False)
    barcode_value = serializers.CharField(required=False)


class ProduitBarcodeOutSerializer(serializers.Serializer):
    produit_id = serializers.IntegerField()
    id_qr = serializers.CharField()
    code_barre = serializers.CharField()
    barcode_value = serializers.CharField()
    barcode_base64_png = serializers.CharField()


class CatalogueSyncOutSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    marchand = serializers.CharField()
    produits = ProduitCatalogueSyncSerializer(many=True)


class AlerteStockSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    quantite_stock = serializers.IntegerField(allow_null=True)
    seuil_alerte = serializers.IntegerField(allow_null=True)
    suivre_stock = serializers.BooleanField()
    en_rupture = serializers.BooleanField()
    urgence = serializers.CharField()  # "rupture" | "seuil"


class ProduitCreerRapideSerializer(serializers.Serializer):
    """Creation rapide d'un produit lors d'un scan inconnu (code_barre + nom + prix)."""

    code_barre = serializers.CharField(max_length=13, min_length=13)
    nom = serializers.CharField(max_length=200)
    prix = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantite = serializers.IntegerField(min_value=1, default=1)
    vente_id = serializers.IntegerField(required=True)

    def validate_code_barre(self, value):
        if not valider_ean13(value):
            raise serializers.ValidationError(
                "Code-barres invalide : doit etre un EAN-13 (13 chiffres avec checksum correct)."
            )
        return value

    def validate_nom(self, value):
        if not str(value).strip():
            raise serializers.ValidationError("Le nom du produit est obligatoire.")
        return value.strip()

    def validate_prix(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Le prix doit etre strictement positif.")
        return value


class ProduitInconnuSerializer(serializers.Serializer):
    """Reponse quand un code-barres scanne n'existe pas dans le catalogue."""

    code_barre = serializers.CharField()
    message = serializers.CharField()
    suggestions = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True
    )
