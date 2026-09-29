# Scannier — Caisse enregistreuse pour marchands ouest-africains

Application de point de vente (POS) mobile-first pour petits commerces en Afrique de l'Ouest.

## Fonctionnalités

- **Scan QR code** — Scanner les produits par photo ou saisie manuelle
- **Gestion des ventes** — Créer, finaliser, annuler des ventes
- **Tickets** — Génération de tickets PDF et impression Bluetooth
- **Stock** — Suivi des quantités avec alertes de seuil
- **Employés** — Gestion multi-utilisateurs (patron / employé)
- **Hors-ligne** — Fonctionne sans internet, synchronisation automatique
- **Catalogue global** — Base de données de produits ouest-africains
- **Mode clair** — Interface épurée, optimisée pour le mobile

## Stack technique

- **Backend** : Django 6.0 + DRF + SimpleJWT
- **Frontend** : HTML/CSS + Tailwind CSS + DaisyUI
- **Base de données** : SQLite (dev) / PostgreSQL (prod)
- **Mobile** : Capacitor (Android/PWA)
- **Auth** : JWT avec rate limiting

## Installation

### Prérequis

- Python 3.12+
- pip

### Développement

```bash
# Cloner le dépôt
git clone https://github.com/VOTRE_USER/scannier.git
cd scannier

# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp .env.example .env

# Initialiser la base de données
python manage.py migrate

# Créer un superuser (patron)
python manage.py createsuperuser

# Peupler le catalogue de référence
python manage.py peupler_references

# Lancer le serveur
python manage.py runserver 0.0.0.0:8000
```

### Accès

- **Application** : http://localhost:8000
- **Admin** : http://localhost:8000/admin/
- **API Docs** : http://localhost:8000/api/docs/

## Structure du projet

```
scannier/
├── comptes/          # Utilisateurs, employés, auth
├── produits/         # Catalogue, stock, QR codes
├── ventes/           # Ventes, lignes, tickets
├── administration/   # Middleware, contrôle, logging
├── frontend/         # Templates, CSS, JS
├── scannier/         # Configuration Django
└── manage.py
```

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/comptes/login/` | Connexion (JWT) |
| GET | `/api/comptes/employes/` | Liste des employés |
| POST | `/api/comptes/employes/ajouter/` | Créer un employé |
| GET | `/api/produits/catalogue-sync/` | Synchroniser le catalogue |
| POST | `/api/produits/creer/` | Créer un produit |
| POST | `/api/ventes/` | Créer une vente |
| POST | `/api/ventes/{id}/lignes/` | Ajouter une ligne |
| POST | `/api/ventes/{id}/finaliser/` | Finaliser la vente |

## Construction APK (Android)

### Prérequis

- Node.js 18+
- Android Studio
- Java JDK 17+

### Build

```bash
# Installer les dépendances Node
npm install

# Build le frontend pour Capacitor
python build_capacitor.py

# Synchroniser avec Android
npx cap sync android

# Ouvrir dans Android Studio
npx cap open android
```

### Dans Android Studio

1. Attendre que Gradle sync soit terminé
2. Menu **Build > Build Bundle(s) / APK(s) > Build APK(s)**
3. L'APK sera dans `android/app/build/outputs/apk/debug/`

### Mode production (API distante)

Modifier `capacitor.config.json` :

```json
{
  "server": {
    "url": "https://votre-api.com",
    "cleartext": false
  }
}
```

Puis relancer `npx cap sync android`.

## Configuration production

```env
DJANGO_DEBUG=False
DJANGO_SECURE=True
DJANGO_SECRET_KEY=cle-longue-et-aleatoire
DJANGO_ALLOWED_HOSTS=vote-domaine.com
DATABASE_URL=postgres://user:pass@host:5432/dbname
FRONTEND_USE_MOCK=False
```

## Licence

MIT
