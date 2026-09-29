import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("scannier.api_errors")


class ApiErrorLoggingMiddleware(MiddlewareMixin):
    """
    Middleware pour logger les erreurs API (4xx/5xx) avec contexte métier.

    Trace :
    - endpoint, méthode HTTP, code de statut
    - marchand/employé concerné (si authentifié)
    - IP, User-Agent
    - message d'erreur clair

    Ne JAMAIS logger : mot de passe, token JWT, Authorization header.
    """

    def process_response(self, request, response):
        # Ne logger que les erreurs 4xx/5xx sur les endpoints API
        if not request.path.startswith("/api/"):
            return response

        status_code = response.status_code
        if status_code < 400:
            return response

        # Construire le contexte
        context = self._build_context(request, response)

        # Message selon le type d'erreur
        message = self._get_error_message(status_code, response)

        logger.warning(
            message,
            extra={
                "status_code": status_code,
                "endpoint": request.path,
                "method": request.method,
                "marchand_id": context.get("marchand_id"),
                "employe_id": context.get("employe_id"),
                "role": context.get("role"),
                "ip": context.get("ip"),
                "user_agent": context.get("user_agent"),
                "error_message": message,
            },
        )

        return response

    def _build_context(self, request, response):
        """Extrait le contexte marchand/employé sans exposer de secrets."""
        context = {
            "marchand_id": None,
            "employe_id": None,
            "role": None,
            "ip": self._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
        }

        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_superuser:
            # Employé (inclut le patron qui a aussi un compte Employe)
            employe = getattr(user, "employe", None)
            if employe:
                context["employe_id"] = employe.id
                context["role"] = employe.role
                context["marchand_id"] = employe.marchand_id
            else:
                # Marchand direct (user.marchand via OneToOne)
                marchand = getattr(user, "marchand", None)
                if marchand:
                    context["marchand_id"] = marchand.id
                    context["role"] = "patron"

        return context

    def _get_client_ip(self, request):
        """Récupère l'IP cliente en tenant compte des proxys."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _get_error_message(self, status_code, response):
        """Génère un message clair selon le code d'erreur."""
        if status_code == 400:
            return "Requête invalide (données malformées ou manquantes)"
        if status_code == 401:
            return "Non authentifié (token manquant ou invalide)"
        if status_code == 403:
            return "Accès refusé (compte suspendu ou permissions insuffisantes)"
        if status_code == 404:
            return "Ressource introuvable"
        if status_code == 405:
            return "Méthode HTTP non autorisée"
        if status_code == 429:
            return "Trop de requêtes (rate limiting)"
        if 500 <= status_code < 600:
            return "Erreur serveur interne"
        return f"Erreur HTTP {status_code}"