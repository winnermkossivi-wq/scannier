from django.contrib.auth.models import User
from django.db.models import Count, Sum
from rest_framework import serializers

from .models import Employe, Marchand
from ventes.models import Vente


class EmployeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    nb_ventes = serializers.IntegerField(read_only=True)
    montant_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    derniere_activite = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Employe
        fields = ["id", "username", "email", "role", "actif", "marchand", "nb_ventes", "montant_total", "derniere_activite"]


class EmployeDetailSerializer(serializers.ModelSerializer):
    """Détail d'un employé avec ses statistiques de vente."""
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    date_creation = serializers.DateTimeField(source="user.date_joined", read_only=True)
    nb_ventes = serializers.IntegerField(read_only=True)
    montant_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    derniere_activite = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Employe
        fields = [
            "id", "username", "email", "role", "actif",
            "date_creation", "nb_ventes", "montant_total", "derniere_activite"
        ]


class CreerEmployeSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6, write_only=True)
    email = serializers.EmailField(required=False, default="")
    role = serializers.ChoiceField(choices=Employe.ROLE_CHOICES, default="employe")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe deja.")
        return value

    def create(self, validated_data):
        marchand = self.context["marchand"]
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
        )
        employe = Employe.objects.create(
            user=user,
            marchand=marchand,
            role=validated_data.get("role", "employe"),
            actif=True,
        )
        return employe
