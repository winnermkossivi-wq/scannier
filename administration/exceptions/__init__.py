"""
Gestionnaire d'exceptions DRF personnalise.

Objectifs :
1. Messages d'erreur uniformes en production (pas de details techniques)
2. Message unique pour login (empeche l'enumeration d'utilisateurs)
3. Pas de stack traces en production
4. Logs structurés pour les erreurs 5xx
"""
import logging
from django.conf import settings

logger = logging.getLogger("scannier.api_errors")


class CompteSuspendu(Exception):
    """Le compte du marchand est suspendu : action sensible bloquee."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _is_production():
    return not settings.DEBUG


def _get_drf_components():
    """Lazy import DRF components to avoid AppRegistryNotReady at module load."""
    from rest_framework.views import exception_handler
    from rest_framework import status
    return exception_handler, status


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions centralise.
    - En production : messages generiques, pas de details techniques
    - Login : message unique "Identifiants invalides" (anti-enumeration)
    - 5xx : log complet + message generique client
    """
    # Lazy import DRF components
    exception_handler, status = _get_drf_components()

    # Appel du handler par defaut DRF
    response = exception_handler(exc, context)

    view = context.get("view")
    request = context.get("request")
    path = request.path if request else ""

    # Detection endpoint de login
    is_login = path.endswith("/comptes/login/") or (
        hasattr(view, "__class__") and "login" in view.__class__.__name__.lower()
    )

    if response is not None:
        # Erreur 400/401/403/404/429 etc. - format standardise
        custom_data = {
            "error": True,
            "code": response.status_code,
        }

        if is_login and response.status_code in (400, 401):
            # Message unique pour empecher l'enumeration d'utilisateurs
            custom_data["message"] = "Identifiants invalides"
            custom_data["detail"] = "Email ou mot de passe incorrect"
        elif response.status_code == 403:
            custom_data["message"] = "Accès refusé"
            custom_data["detail"] = "Permissions insuffisantes ou compte suspendu"
        elif response.status_code == 404:
            custom_data["message"] = "Ressource introuvable"
        elif response.status_code == 429:
            custom_data["message"] = "Trop de requêtes"
            custom_data["detail"] = "Réessayez plus tard"
        elif response.status_code >= 500:
            # En production : message generique, log complet cote serveur
            custom_data["message"] = "Erreur serveur interne"
            if _is_production():
                logger.error(
                    "Internal server error",
                    extra={
                        "status_code": 500,
                        "endpoint": getattr(request, "path", ""),
                        "method": getattr(request, "method", ""),
                        "error": str(exc),
                    },
                )
        else:
            # Autres erreurs 4xx
            custom_data["message"] = "Requête invalide"
            # En prod, on ne retourne pas les details de validation
            if not _is_production() and hasattr(response, "data"):
                custom_data["detail"] = response.data

        response.data = custom_data
        return response

    # Erreur non geree par DRF (500 non capture)
    if _is_production():
        logger.exception(
            "Unhandled exception",
            extra={
                "endpoint": getattr(request, "path", ""),
                "method": getattr(request, "method", ""),
            },
        )
        return None  # Laisser Django gerer (page 500)

    return response