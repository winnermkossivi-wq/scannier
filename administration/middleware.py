from django.http import HttpResponseForbidden


class ControleCompteMiddleware:
    """Verification centrale : bloque toute requete d'un Marchand suspendu.

    - Superuser (proprietaire plateforme) : toujours autorise.
    - Marchand actif : autorise.
    - Marchand suspendu (actif=False) : reponse 403 claire.
    - Abonnement expire ou suspendu : reponse 403 claire.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_superuser:
            # Un employe (y compris un patron qui est aussi un compte marchand)
            # individuellement suspendu doit etre bloque, meme si le marchand
            # est actif.
            employe = getattr(user, "employe", None)
            if employe is not None and not employe.actif:
                return HttpResponseForbidden(
                    "Employe suspendu : cette action est bloquee. "
                    "Contactez le responsable de la boutique."
                )
            # Le marchand (compte principal) suspendu bloque toute action.
            marchand = getattr(user, "marchand", None)
            if marchand is not None:
                if not marchand.actif:
                    return HttpResponseForbidden(
                        "Compte suspendu : cette action est bloquee. "
                        "Contactez l'administrateur de la plateforme."
                    )
                # Verification statut abonnement
                if not marchand.est_abonnement_valide():
                    if marchand.statut_abonnement == "expire":
                        return HttpResponseForbidden(
                            "Abonnement expire : cette action est bloquee. "
                            "Contactez l'administrateur pour renouveler."
                        )
                    elif marchand.statut_abonnement == "suspendu":
                        return HttpResponseForbidden(
                            "Abonnement suspendu : cette action est bloquee. "
                            "Contactez l'administrateur de la plateforme."
                        )
        return self.get_response(request)
