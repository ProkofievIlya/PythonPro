"""Налаштування для pytest: SQLite у пам'яті, locmem-кеш/пошта, без Postgres і Redis."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")

from .settings import *  # noqa: E402,F401,F403

DEBUG = False

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if "debug_toolbar" not in m]  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

ACCOUNT_RATE_LIMITS = False

# Ключі-заглушки: реальний Stripe у тестах не викликається (див. tests/conftest.py).
STRIPE_SECRET_KEY = "sk_test_dummy"
STRIPE_PUBLISHABLE_KEY = "pk_test_dummy"
STRIPE_WEBHOOK_SECRET = "whsec_test"

SOCIALACCOUNT_PROVIDERS = {}
