"""Generation de tickets au format ESC/POS (imprimantes thermiques)."""


def generer_ticket_escpos(vente):
    """Retourne les octets ESC/POS d'un ticket pour la vente donnee.

    Contient l'en-tete du marchand, les lignes (nom x quantite / sous-total),
    le total, un extrait du hash_preuve, puis la commande de coupe.
    """
    parties = [b"\x1b\x40"]  # init imprimante

    parties.append(vente.marchand.nom_boutique.encode("cp850", "replace") + b"\r\n")
    parties.append(b"=" * 32 + b"\r\n")

    for ligne in vente.lignes.all():
        intitule = "{} x{}".format(ligne.produit.nom, ligne.quantite)
        parties.append(intitule.encode("cp850", "replace") + b"\r\n")
        parties.append(
            "  {:>10.2f}".format(ligne.sous_total).encode("cp850", "replace") + b"\r\n"
        )

    parties.append(b"-" * 32 + b"\r\n")
    parties.append(
        "TOTAL: {:.2f}".format(vente.montant_total).encode("cp850", "replace") + b"\r\n"
    )
    if vente.hash_preuve:
        parties.append(b"HASH: " + vente.hash_preuve[:16].encode("ascii") + b"\r\n")
    parties.append(b"\r\n")
    parties.append(b"\x1d\x56\x00")  # coupe papier

    return b"".join(parties)
