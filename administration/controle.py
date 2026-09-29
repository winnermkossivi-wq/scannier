from functools import wraps

from django.core.exceptions import PermissionDenied

from .exceptions import CompteSuspendu


def verifier_compte_actif(marchand):
    """Point de controle centralise : leve CompteSuspendu si le compte est inactif.

    A utiliser depuis les vues sensibles (creation de vente, ajout de produit)
    ou les fonctions de service metier.
    """
    if marchand is None:
        raise CompteSuspendu("Aucun marchand associe a cette action.")
    if not marchand.actif:
        raison = marchand.raison_suspension or "Suspension par l'administrateur."
        raise CompteSuspendu(
            f"Compte suspendu : impossible d'effectuer cette action. Raison : {raison}"
        )
    return True


def marchand_actif_requis(view_func):
    """Decorateur reutilisable sur les vues sensibles d'un marchand.

    Bloque la requete (403) si le marchand connecte a son compte suspendu.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        marchand = getattr(request.user, "marchand", None)
        try:
            verifier_compte_actif(marchand)
        except CompteSuspendu as exc:
            raise PermissionDenied(exc.message)
        return view_func(request, *args, **kwargs)

    return wrapper
