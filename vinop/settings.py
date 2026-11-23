"""
VinOp settings (Django 5.2 LTS).

How this file is organised
--------------------------
Everything that changes between your laptop and the live shop comes from
environment variables, read from a `.env` file in development (see
`.env.example`). Nothing secret is written in code.

Business rules that affect money (shipping price, free-shipping threshold,
shipping countries) live here too, on purpose: they are not editable from the
Studio panel, so only someone with access to the server config can change
what customers pay.

There is no Django admin in this project. Day-to-day work happens in the
team area at /team/ (see team/permissions.py for who can do what).
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Reads .env when it exists (local development). In production the hosting
# platform sets real environment variables and this line does nothing.
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    """Return the variable, or `default` when it is missing or left empty."""
    return os.environ.get(name, "").strip() or default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# ── Core & security ──────────────────────────────────────────────────────────

DEBUG = env_bool("DEBUG", default=False)
TESTING = "test" in sys.argv  # `python manage.py test`

SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if not (DEBUG or TESTING):
        raise ImproperlyConfigured("Set SECRET_KEY in the environment (see .env.example).")
    SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Absolute address of the shop, used to build links inside emails that are
# sent without a browser request (for example from the Stripe webhook).
SITE_URL = env("SITE_URL", "http://localhost:8000").rstrip("/")

if not (DEBUG or TESTING):  # production-only security (the test client speaks plain HTTP)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))  # raise once HTTPS is confirmed
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"


# ── Applications ─────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    # Django
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.forms",  # lets our own form templates override Django's widgets
    # Third party
    "allauth",
    "allauth.account",
    "django_countries",
    # VinOp
    "core",
    "studio",
    "catalog",
    "cart",
    "orders",
    "accounts",
    "wishlist",
    "reviews",
    "newsletter",
    "team",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "vinop.urls"
WSGI_APPLICATION = "vinop.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # required by allauth
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "studio.context_processors.site",
                "cart.context_processors.cart",
                "team.context_processors.team",
            ],
            "builtins": ["core.templatetags.shop"],  # {% icon %}, |money, … in every template
        },
    },
]

# Every {{ form }} in the project renders through templates/forms/*.html,
# so labels, help texts and errors look the same everywhere.
FORM_RENDERER = "core.forms.SiteFormRenderer"


# ── Database ─────────────────────────────────────────────────────────────────
# Local: an SQLite file, zero setup. Production: set DATABASE_URL (Postgres).

# `env()` treats an empty DATABASE_URL= line in .env as "not set" (dj_database_url.config
# would read the empty string and return no database at all).
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ── Authentication (django-allauth 65) ───────────────────────────────────────

AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "accounts:overview"

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", "mandatory")
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = "VinOp – "
# Sends team members to /team/ after login, customers to their profile.
ACCOUNT_ADAPTER = "accounts.adapter.AccountAdapter"


# ── Internationalisation ─────────────────────────────────────────────────────
# English storefront for all of Europe. Strings are wrapped for translation,
# so adding German or Spanish later is `makemessages -l de` + translating.

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True


# ── Static files & uploads ───────────────────────────────────────────────────

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Most hosts wipe the disk on every deploy, so uploaded wine photos need
# external storage in production. Set USE_S3=True plus the AWS_* variables
# (and install django-storages[s3]) to keep them in an S3 bucket.
if env_bool("USE_S3"):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
            "region_name": env("AWS_S3_REGION_NAME", "eu-central-1"),
            "location": "media",
            "file_overwrite": False,
            "querystring_auth": False,
        },
    }

if DEBUG or TESTING:
    # Local runs and the test suite don't need the hashed static manifest
    # (which only exists after `collectstatic`).
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


# ── Messages ─────────────────────────────────────────────────────────────────
# Stored in the session, so a message survives the redirect after a POST.

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"


# ── Shop rules (money: deliberately not editable from the Studio) ────────────

CURRENCY = "EUR"
CURRENCY_SYMBOL = "€"

SHIPPING_FLAT_RATE = Decimal(env("SHIPPING_FLAT_RATE", "9.90"))
FREE_SHIPPING_THRESHOLD = Decimal(env("FREE_SHIPPING_THRESHOLD", "120.00"))

# ISO codes of the countries we deliver to. Default: the 27 EU member states.
SHIPPING_COUNTRIES = env_list(
    "SHIPPING_COUNTRIES",
    "AT,BE,BG,HR,CY,CZ,DK,EE,FI,FR,DE,GR,HU,IE,IT,LV,LT,LU,MT,NL,PL,PT,RO,SK,SI,ES,SE",
)

MAX_BOTTLES_PER_WINE = int(env("MAX_BOTTLES_PER_WINE", "36"))
LOW_STOCK_THRESHOLD = int(env("LOW_STOCK_THRESHOLD", "6"))
WINES_PER_PAGE = 12


# ── Stripe ───────────────────────────────────────────────────────────────────

STRIPE_PUBLIC_KEY = env("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET")
STRIPE_CURRENCY = "eur"


# ── Email ────────────────────────────────────────────────────────────────────
# Development prints every email in the runserver console.

if env_bool("EMAIL_USE_CONSOLE", default=DEBUG):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "VinOp <hello@vinop.example>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# Receives the "new order" alert for every paid order.
STORE_OWNER_EMAIL = env("STORE_OWNER_EMAIL", "orders@vinop.example")


# ── Logging ──────────────────────────────────────────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
