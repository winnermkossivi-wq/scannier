# -*- coding: utf-8 -*-
"""
Migration pour activer Row Level Security (RLS) sur PostgreSQL.
Ignoree sur SQLite (pas de RLS disponible).
"""
from django.db import migrations, connection


def enable_rls(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE IF EXISTS produits_produit ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS ventes_vente ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS ventes_lignevente ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS comptes_employe ENABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS comptes_marchand ENABLE ROW LEVEL SECURITY;

            CREATE POLICY produits_isolation ON produits_produit
                USING (marchand_id = current_setting('app.current_marchand_id')::integer)
                WITH CHECK (marchand_id = current_setting('app.current_marchand_id')::integer);

            CREATE POLICY ventes_isolation ON ventes_vente
                USING (marchand_id = current_setting('app.current_marchand_id')::integer)
                WITH CHECK (marchand_id = current_setting('app.current_marchand_id')::integer);

            CREATE POLICY lignevente_isolation ON ventes_lignevente
                USING (vente_id IN (
                    SELECT id FROM ventes_vente WHERE marchand_id = current_setting('app.current_marchand_id')::integer
                ))
                WITH CHECK (vente_id IN (
                    SELECT id FROM ventes_vente WHERE marchand_id = current_setting('app.current_marchand_id')::integer
                ));

            CREATE POLICY employe_isolation ON comptes_employe
                USING (marchand_id = current_setting('app.current_marchand_id')::integer)
                WITH CHECK (marchand_id = current_setting('app.current_marchand_id')::integer);

            CREATE POLICY marchand_isolation ON comptes_marchand
                USING (id = current_setting('app.current_marchand_id')::integer)
                WITH CHECK (id = current_setting('app.current_marchand_id')::integer);

            ALTER TABLE IF EXISTS produits_produit FORCE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS ventes_vente FORCE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS ventes_lignevente FORCE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS comptes_employe FORCE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS comptes_marchand FORCE ROW LEVEL SECURITY;
        """)


def disable_rls(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        cursor.execute("""
            DROP POLICY IF EXISTS produits_isolation ON produits_produit;
            DROP POLICY IF EXISTS ventes_isolation ON ventes_vente;
            DROP POLICY IF EXISTS lignevente_isolation ON ventes_lignevente;
            DROP POLICY IF EXISTS employe_isolation ON comptes_employe;
            DROP POLICY IF EXISTS marchand_isolation ON comptes_marchand;

            ALTER TABLE IF EXISTS produits_produit DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS ventes_vente DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS ventes_lignevente DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS comptes_employe DISABLE ROW LEVEL SECURITY;
            ALTER TABLE IF EXISTS comptes_marchand DISABLE ROW LEVEL SECURITY;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0005_produit_stock_suivi'),
        ('ventes', '0001_initial'),
        ('comptes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
