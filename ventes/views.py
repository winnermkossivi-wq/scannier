import base64

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from administration.controle import verifier_compte_actif
from administration.exceptions import CompteSuspendu
from comptes.models import Employe
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from produits.models import Produit
from ventes.escpos import generer_ticket_escpos
from ventes.models import LigneVente, Vente
from ventes.serializers import (
    AjoutLigneSerializer,
    LigneVenteSerializer,
    SyncOutSerializer,
    SyncVenteSerializer,
    TicketEscPosOutSerializer,
    VenteSerializer,
)
from produits.serializers import ProduitInconnuSerializer


def get_employe_authentifie(request):
    """Retourne l'Employe lie au user connecte, ou leve PermissionDenied."""
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("Authentification requise.")
    if user.is_superuser:
        raise PermissionDenied("Ce compte n'a pas de scope marchand.")
    try:
        return user.employe
    except Employe.DoesNotExist:
        raise PermissionDenied("Aucun employe associe a ce compte.")


def exiger_compte_actif(emp):
    """Leve PermissionDenied si le Marchand OU l'employe est suspendu."""
    if not emp.actif:
        raise PermissionDenied("Employe suspendu : cette action est bloquee.")
    try:
        verifier_compte_actif(emp.marchand)
    except CompteSuspendu:
        raise PermissionDenied("Compte suspendu : cette action est bloquee.")


def acces_vente(emp, vente_id, modification=False):
    """Vente scopee au Marchand de l'employe.

    - modification=True : un 'employe' ne peut toucher qu'a ses propres ventes ;
      un 'patron' peut toucher a toutes les ventes de son Marchand.
    """
    try:
        vente = Vente.objects.get(id=vente_id, marchand=emp.marchand)
    except Vente.DoesNotExist:
        raise PermissionDenied("Vente introuvable ou hors perimetre.")
    if modification and emp.role == "employe" and vente.employe_id != emp.id:
        raise PermissionDenied("Vous ne pouvez modifier que vos propres ventes.")
    return vente


def _decrementer_stock(vente):
    """Decremente le stock SERVEUR de chaque ligne (jamais fourni par le client).

    La quantite decrementee est `ligne.quantite`, resolue cote serveur a partir
    de l'id_qr scanne. Un produit non suivi (suivre_stock=False) est ignore.
    Aucune valeur de stock n'est lue depuis la requete du client.
    """
    for ligne in vente.lignes.select_related("produit").all():
        produit = ligne.produit
        if not produit.suivre_stock:
            continue
        stock = produit.quantite_stock or 0
        nouveau_stock = max(0, stock - ligne.quantite)
        produit.quantite_stock = nouveau_stock
        # Rupture : stock tombe a 0 ou moins (la vente n'est pas bloquee).
        produit.en_rupture = nouveau_stock <= 0
        produit.save(
            update_fields=["quantite_stock", "en_rupture", "date_modification"]
        )


def _restaurer_stock(vente):
    """Restaure le stock suite a l'annulation d'une vente finalisee."""
    for ligne in vente.lignes.select_related("produit").all():
        produit = ligne.produit
        if not produit.suivre_stock:
            continue
        stock = produit.quantite_stock or 0
        nouveau_stock = stock + ligne.quantite
        produit.quantite_stock = nouveau_stock
        # Re-evaluation de la rupture apres restitution.
        produit.en_rupture = nouveau_stock <= 0
        produit.save(
            update_fields=["quantite_stock", "en_rupture", "date_modification"]
        )


class VenteListeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Liste des ventes",
        description="Historique des ventes. Acces : employe (ses propres ventes) ou patron (tout son marchand).",
        tags=["Ventes"],
        responses={200: VenteSerializer(many=True)},
    )
    def get(self, request):
        """Historique : employe ne voit que ses ventes, patron voit tout son Marchand."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        if emp.role == "employe":
            qs = Vente.objects.filter(employe=emp)
        else:
            qs = Vente.objects.filter(marchand=emp.marchand)
        return Response(VenteSerializer(qs, many=True).data)

    @extend_schema(
        summary="Creer une vente en cours",
        description="Cree une vente en cours pour le marchand/employe connecte. Acces : patron ou employe du marchand.",
        tags=["Ventes"],
        responses={201: VenteSerializer},
    )
    def post(self, request):
        """Cree une vente en cours pour le marchand/employe connecte."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        vente = Vente.objects.create(marchand=emp.marchand, employe=emp, statut="en_cours")
        return Response(VenteSerializer(vente).data, status=status.HTTP_201_CREATED)


class LigneVenteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ajouter une ligne a une vente",
        description="Ajoute une ligne (scan) a une vente en cours du marchand connecte. Acces : employe (sa propre vente) ou patron (toute vente du marchand).",
        tags=["Ventes"],
        request=AjoutLigneSerializer,
        responses={201: LigneVenteSerializer},
    )
    def post(self, request, vente_id):
        """Ajoute une ligne (scan) a une vente en cours du marchand connecte."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        vente = acces_vente(emp, vente_id, modification=True)
        if vente.statut != "en_cours":
            raise PermissionDenied("On ne peut ajouter des lignes qu'a une vente en cours.")
        data = AjoutLigneSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        id_qr = data.validated_data.get("id_qr")
        code_barre = data.validated_data.get("code_barre") or data.validated_data.get("barcode")
        produit_id = data.validated_data.get("produit")
        if code_barre:
            produit = Produit.objects.filter(marchand=emp.marchand, code_barre=code_barre).first()
            if produit is None:
                # fallback: essaye id_qr pour retro-compat
                produit = Produit.objects.filter(marchand=emp.marchand, id_qr=code_barre).first()
        elif id_qr:
            # compat: id_qr peut etre un code_barre
            produit = Produit.objects.filter(marchand=emp.marchand, code_barre=id_qr).first()
            if produit is None:
                produit = Produit.objects.filter(marchand=emp.marchand, id_qr=id_qr).first()
        else:
            produit = Produit.objects.filter(marchand=emp.marchand, id=produit_id).first()
        if produit is None:
            # Produit inconnu : retourne info pour creation rapide coté frontend
            code_scanné = code_barre or id_qr or ""
            suggestions = self._chercher_similaires(emp.marchand, code_scanné)
            return Response(
                ProduitInconnuSerializer({
                    "code_barre": code_scanné,
                    "message": "Produit introuvable dans le catalogue du marchand.",
                    "suggestions": suggestions,
                }).data,
                status=status.HTTP_404_NOT_FOUND,
            )
        ligne = LigneVente.objects.create(
            vente=vente, produit=produit, quantite=data.validated_data["quantite"]
        )
        return Response(LigneVenteSerializer(ligne).data, status=status.HTTP_201_CREATED)

    def _chercher_similaires(self, marchand, code_barre: str):
        """Cherche des produits similaires par nom (prefixe) pour suggestions."""
        if not code_barre:
            return []
        # On cherche d'abord par prefixe de code-barres (EAN-13 partage souvent les premiers chiffres)
        similaires = Produit.objects.filter(
            marchand=marchand, code_barre__startswith=code_barre[:7]
        ).values("id", "nom", "code_barre", "prix")[:5]
        return list(similaires)


class FinaliserVenteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Finaliser une vente",
        description="Finalise une vente (total + hash_preuve calcules cote serveur). Le stock des produits suivis est decremente cote serveur, derive des lignes (jamais fourni par le client). Acces : employe (sa propre vente) ou patron (toute vente du marchand).",
        tags=["Ventes"],
        responses={200: VenteSerializer},
    )
    def post(self, request, vente_id):
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        vente = acces_vente(emp, vente_id, modification=True)
        if vente.statut == "annulee":
            raise PermissionDenied("Vente annulee, impossible a finaliser.")
        deja_finalisee = vente.statut == "finalisee"
        vente.recalculer_montant_total()
        vente.hash_preuve = vente.calculer_hash_preuve()
        vente.statut = "finalisee"
        vente.save(update_fields=["montant_total", "hash_preuve", "statut"])
        if not deja_finalisee:
            # Decrement serveur derive des lignes ; jamais fourni par le client.
            _decrementer_stock(vente)
        return Response(VenteSerializer(vente).data)


class AnnulerVenteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Annuler une vente",
        description="Annule une vente. Acces : employe (sa propre vente) ou patron (toute vente du marchand). Un autre marchand recoit 403.",
        tags=["Ventes"],
        responses={200: VenteSerializer},
    )
    def post(self, request, vente_id):
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        vente = acces_vente(emp, vente_id, modification=True)
        if vente.statut == "annulee":
            raise PermissionDenied("Vente deja annulee.")
        deja_finalisee = vente.statut == "finalisee"
        vente.statut = "annulee"
        vente.save(update_fields=["statut"])
        if deja_finalisee:
            # Restitution du stock suite a l'annulation d'une vente finalisee.
            _restaurer_stock(vente)
        return Response(VenteSerializer(vente).data)




class TicketEscPosView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ticket ESC/POS d'une vente",
        description="Retourne le ticket ESC/POS de la vente, encode en base64. Acces : employe (sa propre vente) ou patron (toute vente du marchand).",
        tags=["Ventes"],
        responses={200: TicketEscPosOutSerializer},
    )
    def get(self, request, vente_id):
        """Retourne le ticket ESC/POS de la vente, encodé en base64."""
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        vente = acces_vente(emp, vente_id)
        donnees = generer_ticket_escpos(vente)
        ticket_b64 = base64.b64encode(donnees).decode("ascii")
        return Response(
            {
                "format": "ESC/POS",
                "vente_id": vente.id,
                "id_unique": str(vente.id_unique),
                "octets": len(donnees),
                "ticket_base64": ticket_b64,
            }
        )


def _resoudre_produit(marchand, ligne):
    """Resolution serveur du produit (on ne fait jamais confiance au client).

    Supporte code_barre (prioritaire), id_qr (compat), ou produit id.
    """
    import uuid as _uuid

    code_barre = (ligne.get("code_barre") or ligne.get("barcode") or "").strip()
    id_qr = (ligne.get("id_qr") or "").strip()
    produit_id = ligne.get("produit")

    # Priorite: code_barre
    if code_barre:
        p = Produit.objects.filter(marchand=marchand, code_barre=code_barre).first()
        if p:
            return p
        # fallback: code_barre peut etre un ancien id_qr
        try:
            _uuid.UUID(str(code_barre))
            q = Produit.objects.filter(marchand=marchand, id_qr=code_barre).first()
            if q:
                return q
        except Exception:
            pass
        return None
    if id_qr:
        # Compat: id_qr peut contenir un code_barre (ancien client) ou vrai UUID
        p = Produit.objects.filter(marchand=marchand, code_barre=id_qr).first()
        if p:
            return p
        try:
            _uuid.UUID(str(id_qr))
        except (ValueError, AttributeError, TypeError):
            return None
        return Produit.objects.filter(marchand=marchand, id_qr=id_qr).first()
    if produit_id:
        return Produit.objects.filter(marchand=marchand, id=produit_id).first()
    return None


class VenteSyncView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Synchroniser un lot de ventes hors-ligne",
        description="Reception d'un lot de ventes creees hors-ligne. Dedoublonnage par (marchand, id_local) ; totaux et hash recalcules cote serveur. Le stock des produits suivis est decremente cote serveur, derive des lignes (jamais fourni par le client). Acces : patron ou employe du marchand.",
        tags=["Ventes"],
        request=SyncVenteSerializer(many=True),
        responses={200: SyncOutSerializer},
    )
    def post(self, request):
        """Synchronise un lot de ventes creees hors-ligne.

        Payload accepte : une liste directe, ou {"ventes": [...]}.
        - Dedoublonnage par (marchand, id_local) : un meme lot renvoye plusieurs
          fois ne cree pas de doublon.
        - montant_total et hash_preuve sont recalcules côté serveur ; les
          valeurs eventuellement envoyees par le client sont ignorees.
        """
        emp = get_employe_authentifie(request)
        exiger_compte_actif(emp)
        marchand = emp.marchand

        donnees = request.data
        if isinstance(donnees, dict) and "ventes" in donnees:
            lot_data = donnees["ventes"]
        else:
            lot_data = donnees

        serializer = SyncVenteSerializer(data=lot_data, many=True)
        serializer.is_valid(raise_exception=True)
        lot = serializer.validated_data

        # 1) Resolution/validation complete AVANT toute ecriture (pas d'etat partiel).
        for item in lot:
            for ligne in item["lignes"]:
                if _resoudre_produit(marchand, ligne) is None:
                    raise serializers.ValidationError(
                        {
                            "lignes": "Produit introuvable dans le catalogue du marchand: "
                            + str(ligne)
                        }
                    )

        # 2) Creation / dedoublonnage.
        resultats = []
        doublons_ignores = 0
        for item in lot:
            id_local = item["id_local"]
            existante = Vente.objects.filter(
                marchand=marchand, id_local=id_local
            ).first()
            if existante is not None:
                doublons_ignores += 1
                resultats.append(self._map(existante, id_local))
                continue

            date_creation = item.get("date_heure_creation") or timezone.now()
            vente = Vente.objects.create(
                marchand=marchand,
                employe=emp,
                statut="finalisee",
                id_local=id_local,
                date_heure_creation=date_creation,
            )
            for ligne in item["lignes"]:
                produit = _resoudre_produit(marchand, ligne)
                LigneVente.objects.create(
                    vente=vente,
                    produit=produit,
                    quantite=ligne["quantite"],
                )
            # Rechargement pour avoir le montant_total recalcule par les lignes.
            vente.refresh_from_db()
            vente.montant_total = vente.recalculer_montant_total()
            vente.hash_preuve = vente.calculer_hash_preuve()
            vente.save(update_fields=["montant_total", "hash_preuve", "statut"])
            # Decrement serveur derive des lignes ; jamais fourni par le client.
            _decrementer_stock(vente)
            resultats.append(self._map(vente, id_local))

        return Response(
            {"resultats": resultats, "doublons_ignores": doublons_ignores}
        )

    @staticmethod
    def _map(vente, id_local):
        return {
            "id_local": id_local,
            "id_unique": str(vente.id_unique),
            "statut": vente.statut,
            "montant_total": str(vente.montant_total),
            "hash_preuve": vente.hash_preuve,
        }
