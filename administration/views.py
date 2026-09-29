from decimal import Decimal
import json
import logging
import re
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from comptes.models import Employe, Marchand
from produits.models import Produit, ProduitReference
from ventes.models import LigneVente, Vente
from administration.serializers import BugReportSerializer, BugReportResponseSerializer


def health_check(request):
    """Endpoint public GET /api/health/ : verifie serveur + base de donnees."""
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Exception:
        db_ok = False

    if db_ok:
        return JsonResponse(
            {"status": "ok", "database": "ok", "timestamp": timezone.now().isoformat()}
        )
    return JsonResponse(
        {"status": "degraded", "database": "error"}, status=503
    )


def _donnees_statistiques():
    """Calcule l'ensemble des statistiques globales (superuser uniquement)."""
    aujourd_hui = timezone.localdate()
    nb_marchands_total = Marchand.objects.count()
    nb_marchands_actifs = Marchand.objects.filter(actif=True).count()
    nb_marchands_suspendus = nb_marchands_total - nb_marchands_actifs

    ventes_jour = Vente.objects.filter(date_heure_creation__date=aujourd_hui)
    nb_ventes_jour = ventes_jour.count()
    montant_jour = ventes_jour.aggregate(total=Sum("montant_total"))["total"] or Decimal(
        "0"
    )
    montant_total = Vente.objects.aggregate(total=Sum("montant_total"))["total"] or Decimal(
        "0"
    )
    nb_produits = Produit.objects.count()

    # Produits les plus vendus, tous marchands confondus (utile pour alimenter
    # plus tard le catalogue ProduitReference).
    plus_vendus = (
        LigneVente.objects.values("produit__nom")
        .annotate(total_vendu=Sum("quantite"))
        .order_by("-total_vendu")[:15]
    )

    # Nombre d'employes actifs par marchand.
    employes_par_marchand = (
        Marchand.objects.annotate(
            nb_employes_actifs=Count(
                "employes", filter=Q(employes__actif=True)
            ),
            nb_employes_total=Count("employes"),
        ).values("nom_boutique", "nb_employes_actifs", "nb_employes_total")
    )

    nb_references = ProduitReference.objects.count()

    return {
        "nb_marchands_total": nb_marchands_total,
        "nb_marchands_actifs": nb_marchands_actifs,
        "nb_marchands_suspendus": nb_marchands_suspendus,
        "nb_produits": nb_produits,
        "nb_references": nb_references,
        "nb_ventes_jour": nb_ventes_jour,
        "montant_jour": str(montant_jour),
        "montant_total": str(montant_total),
        "date_jour": str(aujourd_hui),
        "plus_vendus": list(plus_vendus),
        "employes_par_marchand": list(employes_par_marchand),
    }


@staff_member_required
def statistiques_globales(request):
    if not request.user.is_superuser:
        raise PermissionDenied(
            "Seul le superutilisateur (proprietaire) peut voir les "
            "statistiques globales de la plateforme."
        )

    data = _donnees_statistiques()

    if request.GET.get("format") == "json":
        return JsonResponse(data, json_dumps_params={"indent": 2})

    lignes_plus_vendus = "".join(
        f"<li>{escape(p['produit__nom'])} : <b>{escape(str(p['total_vendu']))}</b> vendus</li>"
        for p in data["plus_vendus"]
    )
    lignes_employes = "".join(
        f"<li>{escape(e['nom_boutique'])} : <b>{escape(str(e['nb_employes_actifs']))}</b> actif(s) "
        f"sur {escape(str(e['nb_employes_total']))} employe(s)</li>"
        for e in data["employes_par_marchand"]
    )

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Scannier - Statistiques plateforme</title></head>
<body>
<h1>Statistiques globales de la plateforme</h1>
<p><a href="/admin/">Retour a l'admin</a> &middot; <a href="?format=json">Voir en JSON</a></p>
<ul>
  <li>Marchands total : <b>{data['nb_marchands_total']}</b></li>
  <li>Marchands actifs : <b>{data['nb_marchands_actifs']}</b></li>
  <li>Marchands suspendus : <b>{data['nb_marchands_suspendus']}</b></li>
  <li>Produits en catalogue (marchands) : <b>{data['nb_produits']}</b></li>
  <li>References catalogue global : <b>{data['nb_references']}</b></li>
  <li>Ventes du jour ({data['date_jour']}) : <b>{data['nb_ventes_jour']}</b></li>
  <li>Montant vendu aujourd'hui : <b>{data['montant_jour']}</b></li>
  <li>Montant total vendu (toutes plateformes) : <b>{data['montant_total']}</b></li>
</ul>
<h2>Produits les plus vendus (tous marchands confondus)</h2>
<ol>{lignes_plus_vendus}</ol>
<h2>Employes actifs par marchand</h2>
<ul>{lignes_employes}</ul>
</body></html>"""
    return HttpResponse(html)


MAX_DESCRIPTION_LENGTH = 2000
DANGEROUS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"on\w+\s*=",
    r"eval\s*\(",
    r"expression\s*\(",
]


def _sanitize_description(text):
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = cleaned[:MAX_DESCRIPTION_LENGTH]
    for pattern in DANGEROUS_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def signaler_bug(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"ok": False, "error": "JSON invalide"},
            status=400,
        )

    raw = payload.get("description", "")
    if not isinstance(raw, str):
        return JsonResponse(
            {"ok": False, "error": "Description requise (chaine)"},
            status=400,
        )

    description = _sanitize_description(raw)
    if not description:
        return JsonResponse(
            {"ok": False, "error": "Description vide ou invalide"},
            status=400,
        )

    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    if not ip:
        ip = request.META.get("REMOTE_ADDR", "")

    user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    print(
        f"[SIGNALEMENT BUG] IP={ip} UA={user_agent} DESC={description[:200]}"
    )

    return JsonResponse({"ok": True, "message": "Signalement recu"})


class SignalerBugView(APIView):
    """
    Endpoint POST /api/support/signaler-bug/

    Permet à un marchand/employé authentifié de signaler un bug
    rencontré dans l'application mobile ou le frontend web.

    Authentification requise : JWT ou Session.
    Rate limiting : 10 requêtes/minute par IP.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Signaler un bug / problème",
        description=(
            "Envoie un signalement de bug avec description libre et contexte technique. "
            "Accessible aux marchands et employés authentifiés. "
            "Rate limiting : 10 requêtes/minute par IP."
        ),
        tags=["Support"],
        request=BugReportSerializer,
        responses={
            201: BugReportResponseSerializer,
            400: OpenApiResponse(description="Données invalides"),
            401: OpenApiResponse(description="Non authentifié"),
            429: OpenApiResponse(description="Trop de requêtes"),
        },
    )
    def post(self, request):
        serializer = BugReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Contexte utilisateur authentifié
        user = request.user
        employe = getattr(user, "employe", None)
        marchand = getattr(user, "marchand", None)
        if employe:
            marchand = employe.marchand

        # Log structuré pour l'équipe support
        support_logger = logging.getLogger("scannier.support")
        support_logger.info(
            "Bug report reçu",
            extra={
                "marchand_id": marchand.id if marchand else None,
                "employe_id": employe.id if employe else None,
                "role": employe.role if employe else ("patron" if marchand else None),
                "version_app": data.get("version_app", ""),
                "action_tentee": data.get("action_tentee", ""),
                "description": data["description"][:200],
                "contexte": data.get("contexte_technique", {}),
            },
        )

        # Générer une référence simple pour le suivi
        reference = f"BUG-{uuid.uuid4().hex[:8].upper()}"

        return Response(
            {
                "status": "received",
                "message": "Signalement enregistré, merci pour votre aide !",
                "reference": reference,
            },
            status=status.HTTP_201_CREATED,
        )
