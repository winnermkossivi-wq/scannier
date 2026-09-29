# Déploiement et sauvegarde — Scannier

Ce document décrit le déploiement en production de Scannier (Django + API REST +
frontend servi par Django) et la stratégie de sauvegarde de la base de données
(PostgreSQL en production).

## 1. Principe général

- La base est le seul état critique (marchands, produits, ventes, tickets).
- Le code et les fichiers statiques sont versionnés : ils ne nécessitent pas de
  sauvegarde à chaud (on redéploie depuis git).
- Objectif : HTTPS partout, secrets hors dépôt, sauvegarde automatique chiffrée,
  rétention et restauration testée.

## 2. Hébergeur recommandé

**Recommandé (contrôle + coût) : VPS Linux + PostgreSQL auto-hébergé.**
- VPS Debian 12 (1 vCPU / 1–2 Go RAM / 10 Go disque minimum) chez Scaleway
  (DEV1), OVH (VPS), DigitalOcean (Droplet) ou Hetzner.
- PostgreSQL installé sur le même VPS (ou bien PostgreSQL managé : Scaleway
  Database, OVH Public Cloud Databases, Render PostgreSQL, Supabase).
- Nom de domaine propre (ex. `caisse.scannier.app`) + DNS (A/AAAA) pointant
  vers le VPS. Accès SSH (clé) pour le déploiement.

**Alternatives 100 % managées (zéro serveur) :** Render, Railway, Fly.io,
Platform.sh, PythonAnywhere. Elles fournissent PostgreSQL en add-on et HTTPS
automatique ; les commandes ci-dessous restent valides (adapter `gunicorn` en
« start command » et les variables d'environnement dans l'interface).

> Le frontend Scannier est rendu par Django (templates + JS statiques). Aucune
> build complexe n'est requise : on sert les pages Django et on expose `/static/`
> via le proxy web.

## 3. Base de données PostgreSQL en production

1. Créer un utilisateur et une base dédiés (à faire une seule fois) :

   ```bash
   sudo -u postgres psql
   CREATE USER scannier WITH PASSWORD 'M0T_DE_PASSE_F0RTE';
   CREATE DATABASE scannier OWNER scannier;
   \q
   ```

2. Renseigner `DATABASE_URL` (dj-database-url la parse automatiquement) :

   ```
   DATABASE_URL=postgres://scannier:M0T_DE_PASSE_F0RTE@127.0.0.1:5432/scannier
   ```

3. Dépendances : `psycopg2-binary` (en test) ou `psycopg2` compilé / `psycopg3`
   en production (déjà listés dans `requirements.txt`). Sur Debian, installer
   `libpq-dev` avant `pip install`.

4. Réglages conseillés (`settings.py` déjà prêt) : connexions réutilisées via
   `CONN_MAX_AGE` si besoin, pas de fichier SQLite en production.

## 4. Variables d'environnement à renseigner

Toutes les configs sensibles viennent de l'environnement (voir `.env.example`).
Copier `.env.example` en `.env` et renseigner :

| Variable | Description | Exemple |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Clé secrète Django (**unique, jamais en dur**) | générée via `get_random_secret_key()` |
| `DJANGO_DEBUG` | `True` dev / **`False` prod** | `False` |
| `DJANGO_SECURE` | **`True` prod** : active HTTPS, HSTS, cookies sécurisés | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés (virgules) | `caisse.scannier.app,www.scannier.app` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Origines du front (virgules) ; vide si front sur le même domaine | `https://caisse.scannier.app` |
| `DJANGO_CORS_ALLOW_CREDENTIALS` | `True` si le front utilise des cookies de session | `False` (on utilise JWT) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origines de confiance CSRF si front sur un autre domaine | `https://caisse.scannier.app` |
| `DJANGO_HSTS_SECONDS` | Durée HSTS (quand `DJANGO_SECURE=True`) | `31536000` |
| `DATABASE_URL` | Connexion PostgreSQL | `postgres://scannier:…@127.0.0.1:5432/scannier` |
| `FRONTEND_USE_MOCK` | **`False` prod** (appel la vraie API) | `False` |
| `DJANGO_API_RATE_ANON` / `DJANGO_API_RATE_USER` | Rate limiting DRF | `60/min`, `1000/hour` |

> Sécurité : un `ImproperlyConfigured` est levé au démarrage si `DEBUG=False`
> avec des hôtes publics mais `DJANGO_SECURE=False` (fail-fast volontaire).

## 5. Commandes de déploiement (VPS Debian + gunicorn + nginx)

```bash
# 1. Récupérer le code
sudo apt update && sudo apt install -y python3-venv python3-pip libpq-dev nginx certbot
git clone <repo> /opt/scannier && cd /opt/scannier

# 2. Environnement virtuel + dépendances
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configuration (éditer .env : SECRET_KEY, DEBUG=False, SECURE=True, ALLOWED_HOSTS, DATABASE_URL…)
cp .env.example .env && nano .env

# 4. Migrations + collecte des statiques
python manage.py migrate
python manage.py collectstatic --noinput --clear

# 5. Service gunicorn (systemd : /etc/systemd/system/scannier.service)
#    ExecStart=/opt/scannier/venv/bin/gunicorn scannier.wsgi:application \
#              --bind 127.0.0.1:8000 --workers 3
sudo systemctl daemon-reload && sudo systemctl enable --now scannier

# 6. nginx : proxy / + HTTPS + /static/
#    location /static/ { alias /opt/scannier/staticfiles/; }
#    location / { proxy_pass http://127.0.0.1:8000;
#                 proxy_set_header X-Forwarded-Proto $scheme; }   # requis pour SECURE_PROXY_SSL_HEADER
sudo certbot --nginx -d caisse.scannier.app
sudo systemctl restart nginx
```

Vérification finale :

```bash
python manage.py check --deploy     # doit être sans avertissement de sécurité
curl -I https://caisse.scannier.app/tableau-de-bord/   # 302 vers /connexion/ (non authentifié)
```

## 6. Sauvegarde PostgreSQL (production)

Ne jamais copier les fichiers de données directement. Utiliser `pg_dump`
(cohérent même en cours d'écriture) :

```bash
# Sauvegarde binaire (restauration rapide)
pg_dump --format=custom --file="backups/scannier_$(date +%Y%m%d_%H%M%S).dump" \
  "postgres://scannier:…@127.0.0.1:5432/scannier"
```

Script de sauvegarde automatique (`/opt/scannier/backup.sh`) exécuté par `cron`
(adapté à l'hébergeur recommandé : VPS en SSH) :

```bash
#!/usr/bin/env bash
set -euo pipefail
DEST=/var/backups/scannier
mkdir -p "$DEST"
F="$DEST/scannier_$(date +%Y%m%d_%H%M%S).dump"
pg_dump --format=custom --file="$F" "$DATABASE_URL"
# Chiffrement au repos (clé publique du responsable ; ou symmetric gpg -c)
gpg --encrypt --recipient backup@scannier.app --output "$F.gpg" "$F" && rm -f "$F"
# Copie vers un stockage externe (object storage / autre VPS)
rclone copy "$F.gpg" remote:scannier-backups/ || true
# Rotation : ne garder que les 24 dernières
ls -1t "$DEST"/*.gpg | tail -n +25 | xargs -r rm -f
```

Planification (`crontab -e`, toutes les heures) :

```cron
0 * * * *  DATABASE_URL=$(grep -oP 'DATABASE_URL=\K.*' /opt/scannier/.env) /opt/scannier/backup.sh
```

Si PostgreSQL managé (Render/Scaleway/…), ces plateformes font **déjà** des
sauvegardes automatiques : conserver leur rétention ET ajouter le `pg_dump`
ci-dessus vers un object storage pour être indépendant du fournisseur.

## 7. Rétention et stockage

- 24 sauvegardes horaires, 7 quotidiennes, 4 hebdomadaires.
- Copier chaque sauvegarde vers un stockage **externe** (object storage chiffré,
  autre région/compte) dans la foulée.
- Chiffrer les fichiers au repos (GPG/clé publique ou SSE-KMS côté fournisseur).

## 8. Restauration (à tester régulièrement !)

```bash
# Déchiffrer si besoin
gpg --decrypt backups/scannier_YYYYMMDD_HHMMSS.dump.gpg > /tmp/scannier.dump
# Restaurer (base préalablement créée/vidée)
pg_restore --clean --if-exists --dbname="$DATABASE_URL" /tmp/scannier.dump
```

Une restauration de test sur un environnement isolé doit être prévue **au moins
une fois par mois** pour valider l'intégrité des sauvegardes.

## 9. Checklist pré-déploiement

- [ ] `SECRET_KEY` défini via env, jamais en dur
- [ ] `DEBUG=False`, `DJANGO_SECURE=True`
- [ ] `ALLOWED_HOSTS` et (si front séparé) `CSRF_TRUSTED_ORIGINS` renseignés
- [ ] `CORS_ALLOWED_ORIGINS` limité aux origines du front
- [ ] `DATABASE_URL` = PostgreSQL (pas de SQLite en prod)
- [ ] `FRONTEND_USE_MOCK=False`
- [ ] HTTPS (certbot) + `X-Forwarded-Proto` transmis par nginx
- [ ] `python manage.py collectstatic` fait, `/static/` servi par nginx
- [ ] Sauvegarde automatique planifiée + restauration testée
- [ ] `python manage.py check --deploy` sans avertissement de sécurité

## 10. Audit sécurité (avant déploiement)

- `python manage.py check --deploy` : **aucun avertissement de sécurité**
  (les seuls messages restants sont `drf_spectacular.W002`, non bloquants,
  relatifs à la génération de la doc OpenAPI).
- `bandit -r scannier comptes produits ventes administration frontend -x "*/migrations/*"` :
  **0 High, 0 Medium**. Les seuls problèmes sont `B106` (mot de passe en dur dans
  des fixtures de test) — faible sévérité, hors production.


## 11. Build et signature de l'APK Android (Capacitor)

> L'application mobile est un wrapper Capacitor qui charge le frontend Django
> servi en HTTPS. Aucun code métier n'est embarqué dans l'APK.

### 11.1 Prérequis

- Android Studio (SDK, build-tools, émulateur) ou `sdkmanager` en CLI
- JDK 17+ (requis pour Gradle 8+ / Android Gradle Plugin 8+)
- Node.js 20+ + `npm` / `npx`
- Compte Google Play Console (pour publication)

### 11.2 Configuration Capacitor (`capacitor.config.json`)

```json
{
  "appId": "app.scannier.caisse",
  "appName": "Scannier",
  "webDir": "www",
  "server": {
    "url": "https://caisse.scannier.app",
    "cleartext": false
  },
  "android": {
    "buildOptions": {
      "keystorePath": "release.keystore",
      "keystoreAlias": "scannier",
      "keystorePassword": "ENV:KEYSTORE_PASSWORD",
      "keyPassword": "ENV:KEY_PASSWORD"
    }
  }
}
```

> Les mots de passe du keystore sont lus via variables d'environnement
> (`KEYSTORE_PASSWORD`, `KEY_PASSWORD`) — **jamais en dur** dans le fichier.

### 11.3 Génération du keystore de release (une seule fois)

```bash
keytool -genkey -v -keystore release.keystore -alias scannier \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass "$KEYSTORE_PASSWORD" -keypass "$KEY_PASSWORD" \
  -dname "CN=Scannier, OU=Mobile, O=Scannier, L=Dakar, C=SN"
```

Stockez `release.keystore` de façon sécurisée (coffre-fort, 1Password, Vault).
**Ne jamais le commiter dans git.**

### 11.4 Build de l'APK de release

```bash
# 1. Installer les dépendances web (si build local nécessaire)
cd /opt/scannier
npm ci

# 2. Synchroniser Capacitor (copie www/ + plugins vers android/)
npx cap sync android

# 3. Build Gradle release (APK signé)
cd android
./gradlew assembleRelease \
  -Pandroid.injected.signing.store.file=../release.keystore \
  -Pandroid.injected.signing.store.password="$KEYSTORE_PASSWORD" \
  -Pandroid.injected.signing.key.alias=scannier \
  -Pandroid.injected.signing.key.password="$KEY_PASSWORD"
```

L'APK signé se trouve dans :
`android/app/build/outputs/apk/release/app-release.apk`

### 11.5 Build de l'AAB (Android App Bundle) pour Google Play

```bash
cd android
./gradlew bundleRelease \
  -Pandroid.injected.signing.store.file=../release.keystore \
  -Pandroid.injected.signing.store.password="$KEYSTORE_PASSWORD" \
  -Pandroid.injected.signing.key.alias=scannier \
  -Pandroid.injected.signing.key.password="$KEY_PASSWORD"
```

L'AAB se trouve dans :
`android/app/build/outputs/bundle/release/app-release.aab`

> **Recommandé** : utiliser l'AAB pour la publication Play Store (optimisation
> dynamique, taille réduite, support App Signing by Google Play).

### 11.6 Vérification de la signature

```bash
# Vérifier l'APK
apksigner verify --print-certs android/app/build/outputs/apk/release/app-release.apk

# Vérifier l'AAB
apksigner verify --print-certs android/app/build/outputs/bundle/release/app-release.aab
```

### 11.7 Publication sur Google Play Console

1. Créer l'application dans Play Console
2. Configurer **Play App Signing** (recommandé : Google gère la clé de signature)
3. Uploader l'AAB (`app-release.aab`)
2. Renseigner les métadonnées (description, captures d'écran, politique de confidentialité)
3. Soumettre pour examen

### 11.8 CI/CD optionnel (GitHub Actions / GitLab CI)

Exemple minimal GitHub Actions (`.github/workflows/android-release.yml`) :

```yaml
name: Android Release
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version name (ex: 1.2.0)'
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: gradle-${{ hashFiles('android/**/*.gradle*') }}
      - name: Setup keystore
        run: |
          echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > release.keystore
      - name: Build AAB
        run: |
          cd android
          ./gradlew bundleRelease \
            -Pandroid.injected.signing.store.file=../release.keystore \
            -Pandroid.injected.signing.store.password="${{ secrets.KEYSTORE_PASSWORD }}" \
            -Pandroid.injected.signing.key.alias=scannier \
            -Pandroid.injected.signing.key.password="${{ secrets.KEY_PASSWORD }}"
      - name: Upload AAB
        uses: actions/upload-artifact@v4
        with:
          name: app-release-aab
          path: android/app/build/outputs/bundle/release/app-release.aab
```

Secrets GitHub requis :
- `KEYSTORE_BASE64` : `base64 -w0 release.keystore`
- `KEYSTORE_PASSWORD`
- `KEY_PASSWORD`
