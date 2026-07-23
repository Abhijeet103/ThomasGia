from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

from prepgia.schema import DEFAULT_DB_PATH, init_db


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUESTION_BANK_DB_PATH = Path(os.getenv("QUESTION_BANK_DB_PATH", str(DEFAULT_DB_PATH)))
init_db(QUESTION_BANK_DB_PATH)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
DJANGO_ENV = os.getenv("DJANGO_ENV", "production").strip().lower()
IS_DEVELOPMENT = DJANGO_ENV == "development"
IS_PRODUCTION = DJANGO_ENV == "production"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,98.94.81.198").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "backend.apps.tenants",
    "backend.apps.accounts",
    "backend.apps.billing",
    "backend.apps.assessments",
    "backend.apps.pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "backend.apps.tenants.middleware.TenantMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "backend.apps.tenants.middleware.TenantAccessMiddleware",
    "backend.apps.billing.middleware.SubscriptionAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "backend.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [ROOT_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "backend.config.wsgi.application"
ASGI_APPLICATION = "backend.config.asgi.application"

def _database_config_from_env():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(DATA_DIR / "django.sqlite3"),
        }

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql", "pgsql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or "5432"),
            # Keep Postgres connections short-lived by default so Supabase's
            # small session pool doesn't get exhausted by idle Django workers.
            "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "0")),
            "CONN_HEALTH_CHECKS": os.getenv("DATABASE_CONN_HEALTH_CHECKS", "True").lower() == "true",
            "OPTIONS": {"sslmode": os.getenv("DATABASE_SSLMODE", "require")},
        }

    if scheme == "sqlite":
        sqlite_path = unquote(parsed.path or "").lstrip("/")
        if parsed.netloc:
            sqlite_path = f"/{parsed.netloc}{parsed.path}"
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_path or str(DATA_DIR / "django.sqlite3"),
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {scheme}")


DATABASES = {"default": _database_config_from_env()}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [ROOT_DIR / "static"]
STATIC_ROOT = ROOT_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
SITE_ID = 2

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FORM_CLASS = "backend.apps.accounts.forms.CustomSignupForm"
SOCIALACCOUNT_ADAPTER = "backend.apps.accounts.adapters.TenantSocialAccountAdapter"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

SOCIALACCOUNT_LOGIN_ON_GET = True

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_AUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_AUTH_CLIENT_SECRET", "")
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000" if IS_DEVELOPMENT else "https://mindmetric.store")
DEFAULT_TENANT_SLUG = os.getenv("DEFAULT_TENANT_SLUG", "mindmetric")
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:8005/0")
FULL_TEST_REDIS_TTL_SECONDS = int(os.getenv("FULL_TEST_REDIS_TTL_SECONDS", "7200"))
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_WEEKLY = os.getenv("STRIPE_PRICE_WEEKLY", "")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")
STRIPE_PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_ENV = os.getenv("PAYPAL_ENV", "sandbox").strip().lower()
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")
PAYPAL_BRAND_NAME = os.getenv("PAYPAL_BRAND_NAME", "MindMetric")

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "0"))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "MindMetric <support@mindmetric.store>")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "support@mindmetric.store")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "support@mindmetric.store")
SALES_INQUIRY_NOTIFICATION_EMAIL = os.getenv("SALES_INQUIRY_NOTIFICATION_EMAIL", "abhijeet179346@gmail.com")
EMAIL_NOTIFICATIONS_ENABLED = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "True").lower() == "true"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "backend.apps.assessments": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "backend.apps.pages": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "backend.apps.billing": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if IS_DEVELOPMENT:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
    SESSION_COOKIE_SECURE = os.getenv("DJANGO_SESSION_COOKIE_SECURE", "True").lower() == "true"
    CSRF_COOKIE_SECURE = os.getenv("DJANGO_CSRF_COOKIE_SECURE", "True").lower() == "true"
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        os.getenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() == "true"
    )
    SECURE_HSTS_PRELOAD = os.getenv("DJANGO_SECURE_HSTS_PRELOAD", "True").lower() == "true"
