"""
Django settings for scannier project.

Configuration securisee : tous les secrets et parametres d'environnement sont
lus depuis les variables d'environnement (voir .env.example). Aucun secret n'est
code en dur dans le depot.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Charge un fichier .env local si present (developpement uniquement).
load_dotenv()

from django.utils.crypto import get_random_string

BASE_DIR = Path(__file__).resolve().parent.parent


def _as_bool(valeur, defaut=False):
    return str(valeur).strip().lower() in ("1", "true", "yes", "on")


def _csv(valeur):
    return [item.strip() for item in str(valeur).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# SECURITE - variables d'environnement
# ---------------------------------------------------------------------------
# SECURITY WARNING: la cle est lue depuis l'environnement (jamais en dur).
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or get_random_string(50)

# DEBUG via variable d'environnement (defaut FALSE en production).
DEBUG = _as_bool(os.environ.get("DJANGO_DEBUG", "False"))

# Mode securise (production) : active HTTPS, cookies securises, HSTS.
SECURE_MODE = _as_bool(os.environ.get("DJANGO_SECURE", "False"))

# Always allow all hosts in development mode for network access
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = _csv(os.environ.get("DJANGO_ALLOWED_HOSTS", ""))

# Si en production avec DEBUG=False, activer le mode sécurisé
if not DEBUG and not SECURE_MODE:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "Configuration non sécurisée : en production (DEBUG=False) avec "
        "ALLOWED_HOSTS defini, DJANGO_SECURE doit être True (HTTPS/HSTS/cookies "
        "securises)."
    )

# Fail-fast : en production (DEBUG=False) avec des hotes exposes, le mode
# securise (HTTPS/HSTS/cookies securises) doit etre active. Sinon on refuse de
# demarrer plutot que d'exposer une appli non securisee.
_SECURE_SAFE_HOSTS = {"localhost", "127.0.0.1", "[::1]", "testserver"}
if not DEBUG and not SECURE_MODE and any(
    h not in _SECURE_SAFE_HOSTS for h in ALLOWED_HOSTS
):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "Configuration non securisee : en production (DEBUG=False) avec "
        "ALLOWED_HOSTS defini, DJANGO_SECURE doit etre True (HTTPS/HSTS/cookies "
        "securises)."
    )


# ---------------------------------------------------------------------------
# INSTALLED_APPS
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "comptes",
    "produits",
    "ventes",
    "administration",
    "frontend",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Timeout global pour eviter blocage indefini (connexion instable client).
    "administration.middleware_timeout.RequestTimeoutMiddleware",
    # RLS : defini app.current_marchand_id pour isolation PostgreSQL.
    "administration.middleware_rls.RLSContextMiddleware",
    # Controle centralise : bloque les actions d'un marchand suspendu.
    "administration.middleware.ControleCompteMiddleware",
    # Logging des erreurs API (4xx/5xx) avec contexte marchand/employe.
    "administration.middleware_api_logging.ApiErrorLoggingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "scannier.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "scannier.wsgi.application"


# ---------------------------------------------------------------------------
# CORS (API front <-> back)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = _csv(os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOW_CREDENTIALS = _as_bool(
    os.environ.get("DJANGO_CORS_ALLOW_CREDENTIALS", "False")
)
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]


# ---------------------------------------------------------------------------
# Django REST Framework + rate limiting
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DJANGO_API_RATE_ANON", "60/min"),
        "user": os.environ.get("DJANGO_API_RATE_USER", "1000/hour"),
        "login": os.environ.get("DJANGO_LOGIN_RATE_LIMIT", "10/min"),
    },
    "EXCEPTION_HANDLER": "administration.exceptions.custom_exception_handler",
}


# ---------------------------------------------------------------------------
# drf-spectacular (documentation Swagger de l'API sur /api/docs/)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Scannier API",
    "DESCRIPTION": (
        "API de caisse/scanner pour marchands ouest-africains "
        "(ventes, produits, employes)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"Bearer": []}],
}


# ---------------------------------------------------------------------------
# SESSIONS & COOKIES (expiration, securite)
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_COOKIE_AGE", "28800"))  # 8h
SESSION_SAVE_EVERY_REQUEST = _as_bool(os.environ.get("DJANGO_SESSION_SAVE_EVERY_REQUEST", "True"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = _as_bool(os.environ.get("DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE", "True"))
SESSION_COOKIE_SECURE = SECURE_MODE
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = SECURE_MODE
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if SECURE_MODE:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = _csv(
        os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
    )

# Referrer policy
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Permissions policy (feature policy)
PERMISSIONS_POLICY = {
    "camera": ["self"],
    "microphone": [],
    "geolocation": [],
    "payment": [],
}


# ---------------------------------------------------------------------------
# CORS (API front <-> back)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = _csv(os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOW_CREDENTIALS = _as_bool(
    os.environ.get("DJANGO_CORS_ALLOW_CREDENTIALS", "False")
)
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]


# ---------------------------------------------------------------------------
# Django REST Framework + rate limiting
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DJANGO_API_RATE_ANON", "60/min"),
        "user": os.environ.get("DJANGO_API_RATE_USER", "1000/hour"),
        "login": os.environ.get("DJANGO_LOGIN_RATE_LIMIT", "10/min"),
    },
    "EXCEPTION_HANDLER": "administration.exceptions.custom_exception_handler",
}


# ---------------------------------------------------------------------------
# drf-spectacular (documentation Swagger de l'API sur /api/docs/)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Scannier API",
    "DESCRIPTION": (
        "API de caisse/scanner pour marchands ouest-africains "
        "(ventes, produits, employes)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"Bearer": []}],
}


# ---------------------------------------------------------------------------
# SESSIONS & COOKIES (expiration, securite)
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_COOKIE_AGE", "28800"))  # 8h
SESSION_SAVE_EVERY_REQUEST = _as_bool(os.environ.get("DJANGO_SESSION_SAVE_EVERY_REQUEST", "True"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = _as_bool(os.environ.get("DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE", "True"))
SESSION_COOKIE_SECURE = SECURE_MODE
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = SECURE_MODE
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if SECURE_MODE:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = _csv(
        os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
    )

# Referrer policy
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Permissions policy (feature policy)
PERMISSIONS_POLICY = {
    "camera": ["self"],
    "microphone": [],
    "geolocation": [],
    "payment": [],
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Configuration PostgreSQL requise pour le multi-tenant + RLS.
# En development local sans DATABASE_URL, on utilise SQLite pour faciliter les tests.
# En production, DATABASE_URL est obligatoire (ex.
# postgres://postgres:postgres@db:5432/scannier).
# Le basculement reel se fait au deploy via la variable d'environnement.

if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60, conn_health_checks=True)}
else:
    # Development local : SQLite pour les tests sans installer PostgreSQL.
    # À remplacer par DATABASE_URL en production ou CI.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"timeout": 20},
        }
    }

# Timeout global pour les requetes HTTP (via middleware + gunicorn)
# Voir aussi: gunicorn --timeout 30 dans le script de deploiement
REQUEST_TIMEOUT = int(os.environ.get("DJANGO_REQUEST_TIMEOUT", "30"))


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Stockage statique pour la production : whitenoise sert directement les
# fichiers (CSS/JS) depuis le meme processus WSGI, avec compression gzip/brotli
# et noms de fichiers versionnes (cache-busting). Aucun serveur separe requis.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# URL de base de l'API, injectee dans les templates (pas de valeur en dur dans
# le JS). Surchargeable via DJANGO_API_BASE (ex. "/api" ou un domaine dedie).
API_BASE = os.environ.get("DJANGO_API_BASE", "/api")

# Reactivation du mode simulation du frontend.
# True  -> le navigateur utilise des donnees simulees (API pas encore prete).
# False -> le navigateur appelle les vrais endpoints /api/... (a brancher).
FRONTEND_USE_MOCK = _as_bool(os.getenv("FRONTEND_USE_MOCK", "0"))

# ---------------------------------------------------------------------------
# SimpleJWT (evite les 401 frequents en dev)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
}

# ---------------------------------------------------------------------------
# Upload fichiers (taille max, types autorises)
# ---------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DJANGO_MAX_UPLOAD_SIZE", "5242880"))  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("DJANGO_MAX_UPLOAD_SIZE", "5242880"))  # 5MB

# Types MIME autorises pour les uploads (valides cote serveur)
ALLOWED_UPLOAD_TYPES = _csv(os.environ.get("DJANGO_ALLOWED_UPLOAD_TYPES", "image/jpeg,image/png,image/webp,application/pdf"))


# ---------------------------------------------------------------------------
# Webhooks / signatures
# ---------------------------------------------------------------------------
WEBHOOK_SECRET_KEY = os.environ.get("WEBHOOK_SECRET_KEY", "")

# Cle publique client (PEM) pour chiffrement cote navigateur si necessaire
CLIENT_PUBLIC_KEY = os.environ.get("CLIENT_PUBLIC_KEY", "")


# ---------------------------------------------------------------------------
# Logging applicatif
# ---------------------------------------------------------------------------
# Logs structurés pour tracer les erreurs API (4xx/5xx) avec contexte
# marchand/employe, sans jamais logger de secrets (mot de passe, token).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "api_error": {
            "format": (
                "[{asctime}] API_ERROR status={status_code} "
                "endpoint={endpoint} method={method} "
                "marchand={marchand_id} employe={employe_id} role={role} "
                "ip={ip} user_agent={user_agent} message={message}"
            ),
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["require_debug_true"],  # Pas de logs verbeux en prod
        },
        "api_errors": {
            "class": "logging.StreamHandler",
            "formatter": "api_error",
            "filters": ["require_debug_false"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "scannier.api_errors": {
            "handlers": ["api_errors"],
            "level": "WARNING",
            "propagate": False,
        },
        "scannier.support": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ---- Row Level Security (RLS) ----
#django-db-rls n'est pas requis : on utilise une variable de session
# app.current_marchand_id définie par RLSContextMiddleware.
# Chaque requête filtrera par marchand_id (vu par le middleware).
# Note: PostgreSQL uniquement. SQLite ne supporte pas RLS.
RLS_ENABLED = _as_bool(os.environ.get("RLS_ENABLED", "False"))