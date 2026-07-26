from .settings import *  # noqa: F403


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["*"]
SITE_URL = "https://mindmetric.store"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_SECURE = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
