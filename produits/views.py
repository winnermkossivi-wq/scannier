import base64
import io

import qrcode
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from produits.models import Produit
from produits.pdf import generer_pdf_etiquettes
from produits.serializers import (
    AlerteStockSerializer,
    CatalogueSyncOutSerializer,
    ProduitBarcodeOutSerializer,
    ProduitCatalogueSerializer,
    ProduitCatalogueSyncSerializer,
    ProduitCreateSerializer,
    ProduitCreerRapideSerializer,
    ProduitInconnuSerializer,
    ProduitQrOutSerializer,
    ProduitTousSerializer,
    ProduitUpdateSerializer,
)
from ventes.views import exiger_compte_actif, get_employe_authentifie
from ventes.models import LigneVente, Vente


def _barcode_base64(value: str) -> str:
    """Genere un code-barres Code128 en PNG base64. Fallback QR si echec."""
    try:
        import barcode
        from barcode.writer import ImageWriter

        code = barcode.get_barcode_class("code128")(str(value), writer=ImageWriter())
        buf = io.BytesIO()
        code.write(buf, options={"module_height": 10, "font_size": 10, "text_distance": 2, "quiet_zone": 2})
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        # fallback QR pour compat
        img = qrcode.make(str(value))
        tampon = io.BytesIO()
        img.save(tampon, format="PNG")
        return base64.b64encode(tampon.getvalue()).decode("ascii")


class CatalogueView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Catalogue produits du marchand",
        description="Liste complete du catalogue du marchand connecte (usage hors-ligne). Acces : patron ou employe du marchand.",
        tags=["Produits"],
        responses={200: ProduitCatalogueSerializer},
    )
    def get(self, request):
        """Catalogue complet du marchand connecte (sync offline de l'appli)."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        produits = Produit.objects.filter(marchand=emp.marchand)
        return Response(ProduitCatalogueSerializer(produits, many=True).data)

    def post(self, request):
        """Alias : creation de produit sur la meme route que le catalogue."""
        return ProduitCreateView().post(request)


class BarcodeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Code-barres PNG d'un produit",
        description="Image code-barres Code128 (code_barre encode) en base64 PNG pour un produit du marchand. Acces : patron ou employe du marchand.",
        tags=["Produits"],
        responses={200: ProduitBarcodeOutSerializer},
    )
    def get(self, request, produit_id):
        """Image code-barres en base64 PNG pour un produit du marchand."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        try:
            produit = Produit.objects.get(id=produit_id, marchand=emp.marchand)
        except Produit.DoesNotExist:
            raise PermissionDenied("Produit introuvable ou hors perimetre.")
        value = produit.barcode_value
        b64 = _barcode_base64(value)
        return Response(
            {
                "produit_id": produit.id,
                "id_qr": str(produit.id_qr),
                "code_barre": produit.code_barre,
                "barcode_value": value,
                "barcode_base64_png": b64,
                "qr_base64_png": b64,  # alias compat
            },
            status=status.HTTP_200_OK,
        )


class QRCodeView(BarcodeView):
    """Alias compat : ancien endpoint QR redirige vers barcode."""

    @extend_schema(
        summary="QR code PNG d'un produit (alias code-barres)",
        description="Alias de /barcode/ pour compat. Retourne un code-barres Code128 (code_barre) au lieu d'un QR.",
        tags=["Produits"],
        responses={200: ProduitQrOutSerializer},
    )
    def get(self, request, produit_id):
        return super().get(request, produit_id)


class CatalogueSyncView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Catalogue synchronise (timestamp)",
        description="Catalogue du marchand + timestamp pour sync incrementale. Acces : patron ou employe du marchand.",
        tags=["Produits"],
        responses={200: CatalogueSyncOutSerializer},
    )
    def get(self, request):
        """Catalogue complet du marchand + timestamp pour sync incrementale.

        Chaque produit porte sa date_modification ; le client peut ne rejouer
        que les produits modifies depuis le timestamp precedent.
        """
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        produits = Produit.objects.filter(marchand=emp.marchand)
        timestamp = timezone.now()
        return Response(
            {
                "timestamp": timestamp.isoformat(),
                "marchand": emp.marchand.nom_boutique,
                "produits": ProduitCatalogueSyncSerializer(produits, many=True).data,
            }
        )


class ProduitCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Creer un produit",
        description="Creation d'un produit. Le marchand et le createur (employe) sont imposes par le serveur. Acces : patron ou employe du marchand.",
        tags=["Produits"],
        request=ProduitCreateSerializer,
        responses={201: ProduitCatalogueSerializer},
    )
    def post(self, request):
        """Creation d'un produit : cree_par et marchand imposes par le serveur."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        serializer = ProduitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verification anti-doublon avant creation
        nom = serializer.validated_data.get("nom", "").strip()
        suggestions = self._chercher_similaires_nom(emp.marchand, nom)
        if suggestions:
            # Retourne les suggestions sans creer le produit
            produit_temp = Produit(
                marchand=emp.marchand,
                cree_par=emp,
                **serializer.validated_data,
            )
            produit_temp.suggestions_doublons = suggestions
            return Response(
                ProduitCreateSerializer(produit_temp).data,
                status=status.HTTP_200_OK,  # 200 = suggestions trouvées, pas créé
            )

        produit = Produit(
            marchand=emp.marchand,
            cree_par=emp,
            **serializer.validated_data,
        )
        produit.save()
        return Response(
            ProduitCatalogueSerializer(produit).data, status=status.HTTP_201_CREATED
        )

    def _chercher_similaires_nom(self, marchand, nom: str):
        """Cherche des produits aux noms similaires (insensible casse/accents, prefixe)."""
        if not nom:
            return []
        from produits.serializers import normaliser_nom

        nom_norm = normaliser_nom(nom)
        # Recherche par prefixe normalisé sur les premiers mots
        mots = nom_norm.split()
        if not mots:
            return []
        prefixe = mots[0][:4] if len(mots[0]) >= 4 else mots[0]
        produits = Produit.objects.filter(marchand=marchand, actif=True).values(
            "id", "nom", "code_barre", "prix"
        )
        suggestions = []
        for p in produits:
            p_norm = normaliser_nom(p["nom"])
            if p_norm.startswith(prefixe) or prefixe in p_norm:
                suggestions.append(p)
            if len(suggestions) >= 5:
                break
        return suggestions


class ProduitCreerRapideView(APIView):
    """Creation rapide d'un produit + ajout à la ligne de vente en une seule action."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Creer un produit rapidement et l'ajouter à la vente",
        description=(
            "Endpoint pour creer un produit à la volée lors d'un scan inconnu "
            "et l'ajouter directement à la ligne de vente en cours. "
            "Retourne la ligne de vente créée."
        ),
        tags=["Produits"],
        request=ProduitCreerRapideSerializer,
        responses={201: None},
    )
    def post(self, request):
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)

        serializer = ProduitCreerRapideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        code_barre = data["code_barre"]
        nom = data["nom"]
        prix = data["prix"]
        quantite = data.get("quantite", 1)
        vente_id = data["vente_id"]

        # Verifier que la vente existe et est en cours
        try:
            vente = Vente.objects.get(id=vente_id, marchand=emp.marchand, statut="en_cours")
        except Vente.DoesNotExist:
            raise PermissionDenied("Vente introuvable ou pas en cours.")

        # Verifier si le code-barres existe déjà pour ce marchand
        if Produit.objects.filter(marchand=emp.marchand, code_barre=code_barre).exists():
            return Response(
                {"detail": "Un produit avec ce code-barres existe deja."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Anti-doublon : chercher noms similaires
        suggestions = self._chercher_similaires_nom(emp.marchand, nom)
        if suggestions:
            return Response(
                {
                    "detail": "Produits similaires trouves.",
                    "suggestions": suggestions,
                    "code_barre": code_barre,
                    "nom_saisi": nom,
                    "prix_saisi": str(prix),
                },
                status=status.HTTP_200_OK,
            )

        # Creer le produit
        produit = Produit.objects.create(
            marchand=emp.marchand,
            cree_par=emp,
            nom=nom,
            prix=prix,
            code_barre=code_barre,
            actif=True,
        )

        # Creer la ligne de vente
        ligne = LigneVente.objects.create(
            vente=vente, produit=produit, quantite=quantite
        )

        from ventes.serializers import LigneVenteSerializer

        return Response(
            LigneVenteSerializer(ligne).data, status=status.HTTP_201_CREATED
        )

    def _chercher_similaires_nom(self, marchand, nom: str):
        """Cherche des produits aux noms similaires (insensible casse/accents, prefixe)."""
        if not nom:
            return []
        from produits.serializers import normaliser_nom

        nom_norm = normaliser_nom(nom)
        mots = nom_norm.split()
        if not mots:
            return []
        prefixe = mots[0][:4] if len(mots[0]) >= 4 else mots[0]
        produits = Produit.objects.filter(marchand=marchand, actif=True).values(
            "id", "nom", "code_barre", "prix"
        )
        suggestions = []
        for p in produits:
            p_norm = normaliser_nom(p["nom"])
            if p_norm.startswith(prefixe) or prefixe in p_norm:
                suggestions.append(p)
            if len(suggestions) >= 5:
                break
        return suggestions


class ProduitUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mettre a jour un produit (stock / suivi / seuil / prix / actif)",
        description="Mise a jour partielle d'un produit. Le champ quantite_stock reste une saisie manuelle autorisee du marchand (validee >= 0) ; il est distinct de la decrement automatique cote serveur lors des ventes. Acces : patron ou employe du marchand (le produit doit appartenir au marchand).",
        tags=["Produits"],
        request=ProduitUpdateSerializer,
        responses=ProduitUpdateSerializer,
    )
    def patch(self, request, produit_id):
        """Mise a jour partielle (centree sur le suivi de stock)."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        produit = get_object_or_404(Produit, id=produit_id, marchand=emp.marchand)
        serializer = ProduitUpdateSerializer(produit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        produit = serializer.save()
        return Response(ProduitCatalogueSerializer(produit).data)

    def delete(self, request, produit_id):
        """Supprime un produit (ou le desactive si des ventes y sont liees)."""
        if request.user.is_superuser:
            produit = get_object_or_404(Produit, id=produit_id)
        else:
            emp = get_employe_authentifie(request)
            exiger_compte_actif(emp)
            produit = get_object_or_404(Produit, id=produit_id, marchand=emp.marchand)
        # Si des lignes de vente existent, on ne peut pas hard delete (PROTECT) -> soft delete
        if produit.lignes_vente.exists():
            produit.actif = False
            produit.save(update_fields=["actif", "date_modification"])
            return Response({"detail": "Produit desactive (ventes existantes, code-barres conserve).", "actif": False}, status=status.HTTP_200_OK)
        produit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AlertesStockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Alertes de stock",
        description="Produits du marchand connecte dont le suivi est actif (suivre_stock=True) et dont le stock est inferieur ou egal au seuil. Le seuil est, par produit, son propre champ seuil_alerte s'il est defini, sinon un seuil par defaut (5, configurable via le parametre ?seuil=). Un produit en rupture (stock <= 0) est signale en urgence 'rupture' et porte en_rupture=True. Acces : patron/employe (son marchand) ; un superuser voit toutes les boutiques.",
        tags=["Produits"],
        responses=AlerteStockSerializer(many=True),
    )
    def get(self, request):
        """Produits sous le seuil (defaut 5, ou ?seuil=), pour le marchand connecte."""
        if request.user.is_superuser:
            produits = Produit.objects.all()
        else:
            emp = get_employe_authentifie(request)
            exiger_compte_actif(emp)
            produits = Produit.objects.filter(marchand=emp.marchand)

        # Seuil par defaut configurable via ?seuil= (sinon 5).
        try:
            seuil_defaut = int(request.query_params.get("seuil", 5))
        except (ValueError, TypeError):
            seuil_defaut = 5
        if seuil_defaut < 0:
            seuil_defaut = 0

        alertes = []
        for p in produits:
            if not p.suivre_stock:
                continue
            qs = p.quantite_stock
            if qs is None:
                continue
            # Seuil effectif : celui du produit s'il est defini, sinon le defaut.
            seuil = p.seuil_alerte if p.seuil_alerte is not None else seuil_defaut
            if qs > seuil:
                continue
            urgence = "rupture" if qs <= 0 else "seuil"
            alertes.append(
                {
                    "id": p.id,
                    "nom": p.nom,
                    "quantite_stock": qs,
                    "seuil_alerte": p.seuil_alerte,
                    "suivre_stock": True,
                    "en_rupture": p.en_rupture,
                    "urgence": urgence,
                }
            )
        return Response(AlerteStockSerializer(alertes, many=True).data)


class ProduitTousView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Tous les produits (patron / superuser)",
        description="Tous les produits. Acces : patron (sa propre boutique) ou superuser (toutes les boutiques). Un employe simple recoit 403.",
        tags=["Produits"],
        responses={200: ProduitTousSerializer(many=True)},
    )
    def get(self, request):
        """Tous les produits, reserve au patron (sa boutique) ou au superuser (tout).

        - patron : produits de SON marchand, tous employes confondus.
        - superuser : produits de TOUTES les boutiques.
        - employe simple : interdit.
        """
        user = request.user
        if user.is_superuser:
            produits = Produit.objects.all()
        else:
            emp = get_employe_authentifie(request)
            if emp.role != "patron":
                raise PermissionDenied("Acces reserve au patron ou au superuser.")
            exiger_compte_actif(emp)
            produits = Produit.objects.filter(marchand=emp.marchand)
        produits = produits.select_related(
            "cree_par", "cree_par__user", "marchand", "reference"
        ).order_by("nom")
        return Response(ProduitTousSerializer(produits, many=True).data)


class ProduitQrPdfView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="PDF etiquettes code-barres d'un produit",
        description="PDF de N etiquettes identiques (code-barres Code128 + nom + prix) pour un produit. Acces : proprietaire du marchand (patron ou employe), ou superuser (toute boutique). Un autre marchand recoit 403.",
        tags=["Produits"],
        responses={
            200: OpenApiResponse(
                OpenApiTypes.BINARY, description="PDF des etiquettes code-barres."
            )
        },
    )
    def get(self, request, produit_id):
        """PDF de N etiquettes identiques (code-barres + nom + prix) pour un produit.

        Permissions identiques a la consultation du produit : le marchand /
        employe proprietaire, le patron du marchand, ou un superuser.
        """
        quantite = request.GET.get("quantite", "1")
        try:
            quantite = max(1, min(int(quantite), 100))
        except (ValueError, TypeError):
            quantite = 1

        user = request.user
        if user.is_superuser:
            try:
                produit = Produit.objects.get(id=produit_id)
            except Produit.DoesNotExist:
                raise PermissionDenied("Produit introuvable.")
        else:
            emp = get_employe_authentifie(request)
            exiger_compte_actif(emp)
            try:
                produit = Produit.objects.get(id=produit_id, marchand=emp.marchand)
            except Produit.DoesNotExist:
                raise PermissionDenied("Produit introuvable ou hors perimetre.")

        pdf = generer_pdf_etiquettes(produit, quantite)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="etiquettes_{produit.id}.pdf"'
        )
        return response
