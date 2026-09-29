import logging
import time

from django.conf import settings
from django.db import connections
from django.http import HttpResponse

logger = logging.getLogger("scannier.api_errors")


class RequestTimeoutMiddleware:
    """
    Middleware pour détecter et logger les requêtes lentes.

    En production (gunicorn + nginx), les timeouts sont gérés par :
    - gunicorn --timeout (défaut 30s)
    - nginx proxy_read_timeout (défaut 60s)

    Ce middleware log simplement les requêtes qui dépassent un seuil
    (configurable via DJANGO_REQUEST_TIMEOUT) pour alerter sur les
    endpoints lents sans bloquer le thread principal.

    Pour les tests SQLite, évite le threading qui cause des verrous DB.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_threshold = getattr(settings, "REQUEST_TIMEOUT", 30)

    def __call__(self, request):
        # On ne surveille que les endpoints API
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start

        # Log si la requête dépasse le seuil
        if duration > self.slow_threshold:
            logger.warning(
                "Requête lente détectée",
                extra={
                    "status_code": response.status_code,
                    "endpoint": request.path,
                    "method": request.method,
                    "marchand_id": None,
                    "employe_id": None,
                    "role": None,
                    "ip": self._get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                    "message": f"Durée {duration:.2f}s > seuil {self.slow_threshold}s",
                },
            )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")