"""
Vues d'authentification avec rate limiting.
Vues API pour la gestion des employes.
"""
from django.contrib.auth.models import User
from django.db.models import Count, Max, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle

from .models import Employe
from .serializers import CreerEmployeSerializer, EmployeSerializer, EmployeDetailSerializer
from ventes.models import Vente
from ventes.serializers import VenteSerializer


class LoginRateThrottle(AnonRateThrottle):
    """Rate limiting specifique pour la page de connexion."""
    scope = "login"


class LoginView(TokenObtainPairView):
    """
    Vue de connexion avec rate limiting renforce.
    """
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class EmployeListView(APIView):
    """Liste les employes du marchand authentifie avec stats de vente."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut gerer les employes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        employes = Employe.objects.filter(marchand=employe.marchand).select_related("user").annotate(
            nb_ventes=Count("ventes_employe"),
            montant_total=Sum("ventes_employe__montant_total"),
            derniere_activite=Max("ventes_employe__date_heure_creation")
        )
        serializer = EmployeSerializer(employes, many=True)
        return Response(serializer.data)


class EmployeCreateView(APIView):
    """Cree un nouvel employe pour le marchand authentifie."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut ajouter des employes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CreerEmployeSerializer(
            data=request.data,
            context={"marchand": employe.marchand},
        )
        serializer.is_valid(raise_exception=True)
        new_employe = serializer.save()
        return Response(
            EmployeSerializer(new_employe).data,
            status=status.HTTP_201_CREATED,
        )


class EmployeDeleteView(APIView):
    """Supprime un employe (desactive le lien)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut supprimer des employes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            cible = Employe.objects.get(pk=pk, marchand=employe.marchand)
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Employe non trouve."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if cible.role == "patron":
            return Response(
                {"detail": "Impossible de supprimer le patron."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cible.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmployeDetailView(APIView):
    """Détail d'un employé avec ses statistiques (patron uniquement)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut voir les détails des employés."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            cible = Employe.objects.filter(marchand=employe.marchand).annotate(
                nb_ventes=Count("ventes_employe"),
                montant_total=Sum("ventes_employe__montant_total"),
                derniere_activite=Max("ventes_employe__date_heure_creation")
            ).get(pk=pk)
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Employe non trouve."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = EmployeDetailSerializer(cible)
        return Response(serializer.data)


class EmployeToggleView(APIView):
    """Suspendre ou réactiver un employé (patron uniquement)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut modifier les employés."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            cible = Employe.objects.get(pk=pk, marchand=employe.marchand)
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Employe non trouve."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if cible.role == "patron":
            return Response(
                {"detail": "Impossible de suspendre le patron."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cible.actif = not cible.actif
        cible.save(update_fields=["actif"])
        return Response(
            {"detail": f"Employé {'réactivé' if cible.actif else 'suspendu'} avec succès.", "actif": cible.actif},
            status=status.HTTP_200_OK,
        )


class EmployeVentesView(APIView):
    """Ventes d'un employé (patron uniquement)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut voir les ventes des employés."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            cible = Employe.objects.get(pk=pk, marchand=employe.marchand)
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Employe non trouve."},
                status=status.HTTP_404_NOT_FOUND,
            )
        ventes = Vente.objects.filter(employe=cible).order_by("-date_heure_creation")
        # Stats
        total_ventes = ventes.count()
        total_montant = ventes.aggregate(total=Sum("montant_total"))["total"] or 0
        serializer = VenteSerializer(ventes, many=True)
        return Response({
            "employe": {"id": cible.id, "username": cible.user.username},
            "stats": {"nb_ventes": total_ventes, "montant_total": str(total_montant)},
            "ventes": serializer.data,
        })


class EmployeStatsView(APIView):
    """Statistiques de vente par employé (patron uniquement)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employe = request.user.employe
        except Employe.DoesNotExist:
            return Response(
                {"detail": "Aucun employe associe a ce compte."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if employe.role != "patron":
            return Response(
                {"detail": "Seul le patron peut voir les statistiques des employés."},
                status=status.HTTP_403_FORBIDDEN,
            )
        employes = Employe.objects.filter(marchand=employe.marchand).annotate(
            nb_ventes=Count("ventes_employe"),
            montant_total=Sum("ventes_employe__montant_total"),
            derniere_activite=Max("ventes_employe__date_heure_creation")
        )
        data = [
            {
                "id": e.id,
                "username": e.user.username,
                "role": e.role,
                "actif": e.actif,
                "nb_ventes": e.nb_ventes or 0,
                "montant_total": str(e.montant_total or 0),
                "derniere_activite": e.derniere_activite,
            }
            for e in employes
        ]
        return Response(data)
