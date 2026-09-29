"""Peuple le catalogue global ProduitReference avec des produits courants de boutique ouest-africaine."""

from django.core.management.base import BaseCommand

from produits.models import ProduitReference

VERSION_CATALOGUE = "v2024.1"


PRODUITS = [
    # Alimentaire - bases
    ("Riz", "Alimentaire - base"),
    ("Riz parfume", "Alimentaire - base"),
    ("Sucre", "Alimentaire - base"),
    ("Sel", "Alimentaire - base"),
    ("Farine de ble", "Alimentaire - base"),
    ("Semoule", "Alimentaire - base"),
    ("Pates alimentaires", "Alimentaire - base"),
    ("Couscous", "Alimentaire - base"),
    ("Mais", "Alimentaire - base"),
    ("Mil", "Alimentaire - base"),
    ("Boulgour", "Alimentaire - base"),
    ("Pain", "Alimentaire - base"),
    # Huiles et graisses
    ("Huile de palme", "Huiles et graisses"),
    ("Huile de tournesol", "Huiles et graisses"),
    ("Huile d'arachide", "Huiles et graisses"),
    ("Beurre de cacao", "Huiles et graisses"),
    ("Margarine", "Huiles et graisses"),
    # Boissons
    ("Eau en bouteille", "Boissons"),
    ("Soda", "Boissons"),
    ("Jus de fruit", "Boissons"),
    ("Biere", "Boissons"),
    ("The", "Boissons"),
    ("Cafe", "Boissons"),
    ("Lait en poudre", "Boissons"),
    ("Lait frais", "Boissons"),
    ("Bissap", "Boissons"),
    ("Gingembre (jus)", "Boissons"),
    # Hygiene et beaute
    ("Savon de toilette", "Hygene et beaute"),
    ("Savon de lessive", "Hygene et beaute"),
    ("Dentifrice", "Hygene et beaute"),
    ("Shampoing", "Hygene et beaute"),
    ("Gel douche", "Hygene et beaute"),
    ("Creme hydratante", "Hygene et beaute"),
    ("Couche pour bebe", "Hygene et beaute"),
    # Foyer
    ("Allumettes", "Foyer"),
    ("Bougie", "Foyer"),
    ("Charbon de bois", "Foyer"),
    ("Gaz butane", "Foyer"),
    ("Papier aluminium", "Foyer"),
    # Sucreries
    ("Bonbons", "Sucreries"),
    ("Chocolat", "Sucreries"),
    ("Gateau sec", "Sucreries"),
    ("Biscuits", "Sucreries"),
    # Conserves
    ("Tomate concentree", "Conserves"),
    ("Sardines en boite", "Conserves"),
    ("Mackerel en boite", "Conserves"),
    ("Haricots en boite", "Conserves"),
    ("Confiture", "Conserves"),
    # Epices et condiments
    ("Poivre", "Epices et condiments"),
    ("Piment", "Epices et condiments"),
    ("Gingembre en poudre", "Epices et condiments"),
    ("Curcuma", "Epices et condiments"),
    ("Cube de bouillon", "Epices et condiments"),
    ("Oignon", "Epices et condiments"),
    ("Ail", "Epices et condiments"),
    # Legumes et fruits secs
    ("Haricots secs", "Legumes et fruits secs"),
    ("Pois chiches", "Legumes et fruits secs"),
    ("Arachides", "Legumes et fruits secs"),
    ("Banane plantain", "Legumes et fruits secs"),
    ("Manioc", "Legumes et fruits secs"),
    ("Patate douce", "Legumes et fruits secs"),
]


class Command(BaseCommand):
    help = "Peuple le catalogue global ProduitReference avec des produits courants."

    def handle(self, *args, **options):
        cree = 0
        for nom, categorie in PRODUITS:
            _, made = ProduitReference.objects.get_or_create(
                nom=nom, categorie=categorie, defaults={"version": VERSION_CATALOGUE}
            )
            if made:
                cree += 1
        # Mise a jour de la version pour les existants
        ProduitReference.objects.filter(version="").update(version=VERSION_CATALOGUE)
        self.stdout.write(
            self.style.SUCCESS(
                f"{cree} reference(s) ajoutee(s) sur {len(PRODUITS)} produits du catalogue. Version : {VERSION_CATALOGUE}"
            )
        )
