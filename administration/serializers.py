from rest_framework import serializers


class BugReportSerializer(serializers.Serializer):
    """Signalement de bug depuis l'application mobile/front."""

    description = serializers.CharField(
        max_length=5000,
        help_text="Description libre du problème rencontré par l'utilisateur.",
    )
    action_tentee = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Dernière action tentée (ex: 'scan produit', 'finaliser vente').",
    )
    version_app = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Version de l'application (ex: '1.2.3', '1.2.3-android').",
    )
    contexte_technique = serializers.JSONField(
        required=False,
        default=dict,
        help_text=(
            "Contexte technique optionnel (ex: {'os': 'Android 14', "
            "'device': 'Pixel 7', 'network': '4G'})."
        ),
    )


class BugReportResponseSerializer(serializers.Serializer):
    """Réponse à la création d'un signalement."""

    status = serializers.CharField(default="received")
    message = serializers.CharField()
    reference = serializers.CharField()