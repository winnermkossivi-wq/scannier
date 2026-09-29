"""
Middleware pour definir la variable de session PostgreSQL `app.current_marchand_id`
necessaire aux policies RLS (Row Level Security).

Cette variable est utilisee par les policies RLS pour isoler les donnees par marchand.
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import connection

logger = logging.getLogger(__name__)


class RLSContextMiddleware(MiddlewareMixin):
    """
    Definit la variable de session `app.current_marchand_id` sur chaque requete
    pour que les policies RLS PostgreSQL puissent filtrer les lignes par marchand.
    """

    def process_request(self, request):
        # Ne rien faire sur SQLite
        if connection.vendor != 'postgresql':
            return

        # Recuperer l'ID du marchand depuis l'utilisateur authentifie
        marchand_id = None

        user = getattr(request, 'user', None)
        if user and user.is_authenticated and not user.is_superuser:
            # Employe (inclut patron qui a aussi un compte Employe)
            employe = getattr(user, 'employe', None)
            if employe:
                marchand_id = employe.marchand_id
            else:
                # Marchand direct (user.marchand via OneToOne)
                marchand = getattr(user, 'marchand', None)
                if marchand:
                    marchand_id = marchand.id

        if marchand_id is not None:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET LOCAL app.current_marchand_id = %s",
                        [marchand_id]
                    )
            except Exception as e:
                logger.warning(f"Impossible de definir app.current_marchand_id: {e}")

    def process_response(self, request, response):
        # Reset optionnel (LOCAL se reset automatiquement a la fin de la transaction)
        return response