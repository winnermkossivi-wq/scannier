from administration.controle import verifier_compte_actif

from .models import LigneVente, Vente


def creer_vente(marchand, statut="en_cours"):
    """Cree une vente pour un marchand, apres verification centrale du compte."""
    verifier_compte_actif(marchand)
    return Vente.objects.create(marchand=marchand, statut=statut)


def ajouter_ligne_vente(vente, produit, quantite):
    """Ajoute une ligne a une vente, apres verification centrale du compte."""
    verifier_compte_actif(vente.marchand)
    return LigneVente.objects.create(
        vente=vente, produit=produit, quantite=quantite
    )
