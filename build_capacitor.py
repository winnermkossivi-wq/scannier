"""
Script de build pour Capacitor.
Exporte les templates Django et les fichiers statiques vers www/
pour que l'application puisse fonctionner en mode hors-ligne.

Usage : python build_capacitor.py
"""
import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static" / "frontend"
TEMPLATE_DIR = FRONTEND_DIR / "templates" / "frontend"
WWW_DIR = BASE_DIR / "www"

# Pages a exporter (template -> fichier de sortie)
PAGES = {
    "login.html": "login.html",
    "dashboard.html": "index.html",
    "nouvelle_vente.html": "ventes/nouvelle.html",
    "historique.html": "ventes/historique.html",
    "produits.html": "produits/index.html",
    "tous_produits.html": "produits/catalogue.html",
    "ticket.html": "ventes/ticket.html",
}


def clean_www():
    """Supprime et recree le dossier www/."""
    if WWW_DIR.exists():
        shutil.rmtree(WWW_DIR)
    WWW_DIR.mkdir(parents=True)
    print("[OK] Dossier www/ nettoye")


def copy_static():
    """Copie les fichiers statiques (CSS, JS, icons)."""
    dest = WWW_DIR / "static" / "frontend"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(STATIC_DIR, dest)
    print(f"[OK] Statiques copies vers {dest}")


def build_pages():
    """Exporte les templates Django en HTML statique."""
    for template_name, output_name in PAGES.items():
        src = TEMPLATE_DIR / template_name
        dest = WWW_DIR / output_name

        if not src.exists():
            print(f"[SKIP] Template introuvable : {template_name}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)

        content = src.read_text(encoding="utf-8")

        # Remplacer les URLs Django par des chemins locaux
        # {% static 'frontend/...' %} -> static/frontend/...
        content = content.replace("{% static 'frontend/", "static/frontend/")
        content = content.replace("' %}", "")
        content = content.replace('"%}', "")

        # Supprimer les balises Django template
        content = content.replace("{% load static %}", "")
        content = content.replace("{% csrf_token %}", "")

        # Gerer les blocs Django (garder le contenu principal)
        # Supprimer les extends
        content = content.replace(
            "{% extends 'frontend/base.html' %}", ""
        )

        # Supprimer les blocs et les labels
        import re
        content = re.sub(r'\{%\s*block\s+\w+\s*%\}', '', content)
        content = re.sub(r'\{%\s*endblock\s*%\}', '', content)

        # Supprimer les if/endif
        content = re.sub(r'\{%\s*if\s+[^%]*%\}', '', content)
        content = re.sub(r'\{%\s*elif\s+[^%]*%\}', '', content)
        content = re.sub(r'\{%\s*else\s*%\}', '', content)
        content = re.sub(r'\{%\s*endif\s*%\}', '', content)

        # Supprimer les for/endfor
        content = re.sub(r'\{%\s*for\s+[^%]*%\}', '', content)
        content = re.sub(r'\{%\s*endfor\s*%\}', '', content)

        # Supprimer les url tags
        content = re.sub(r'\{%\s*url\s+[^%]*%\}', '#', content)

        dest.write_text(content, encoding="utf-8")
        print(f"[OK] Page exportee : {output_name}")


def build_base():
    """Exporte base.html comme page principale."""
    src = TEMPLATE_DIR / "base.html"
    if not src.exists():
        print("[SKIP] base.html introuvable")
        return

    content = src.read_text(encoding="utf-8")

    # Remplacer les URLs statiques
    content = content.replace("{% static 'frontend/", "static/frontend/")
    content = content.replace("' %}", "")
    content = content.replace('"%}', "")
    content = content.replace("{% load static %}", "")

    # Supprimer les balises Django
    import re
    content = re.sub(r'\{%\s*block\s+\w+\s*%\}', '', content)
    content = re.sub(r'\{%\s*endblock\s*%\}', '', content)
    content = re.sub(r'\{%\s*if\s+[^%]*%\}', '', content)
    content = re.sub(r'\{%\s*elif\s+[^%]*%\}', '', content)
    content = re.sub(r'\{%\s*else\s*%\}', '', content)
    content = re.sub(r'\{%\s*endif\s*%\}', '', content)
    content = re.sub(r'\{%\s*url\s+[^%]*%\}', '#', content)
    content = re.sub(r'\{\{[^}]*\}\}', '', content)

    (WWW_DIR / "base.html").write_text(content, encoding="utf-8")
    print("[OK] base.html exporte")


def build_manifest():
    """Cree le manifest PWA."""
    manifest = {
        "name": "Scannier - Caisse enregistreuse",
        "short_name": "Scannier",
        "start_url": "index.html",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#000000",
        "orientation": "portrait",
        "icons": [
            {
                "src": "static/frontend/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "static/frontend/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }

    import json
    (WWW_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("[OK] manifest.json cree")


def build_service_worker():
    """Cree le service worker pour le cache hors-ligne."""
    sw = """
const CACHE_NAME = 'scannier-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/login.html',
  '/static/frontend/css/style.css',
  '/static/frontend/js/app.js',
  '/static/frontend/js/api.js',
  '/static/frontend/js/vente.js',
  '/static/frontend/js/produits.js',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
"""
    (WWW_DIR / "sw.js").write_text(sw, encoding="utf-8")
    print("[OK] Service worker cree")


def main():
    print("=== Build Capacitor Scannier ===\n")
    clean_www()
    copy_static()
    build_pages()
    build_base()
    build_manifest()
    build_service_worker()
    print(f"\n=== Termine ! Dossier www/ pret ({WWW_DIR}) ===")


if __name__ == "__main__":
    main()
