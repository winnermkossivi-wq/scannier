from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("produits", "0004_produit_cree_par"),
    ]

    operations = [
        migrations.AddField(
            model_name="produit",
            name="suivre_stock",
            field=models.BooleanField(
                default=False, help_text="Suivre le stock de ce produit."
            ),
        ),
        migrations.AddField(
            model_name="produit",
            name="seuil_alerte",
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text="Seuil d'alerte (stock bas).",
            ),
        ),
    ]
