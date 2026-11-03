"""Локальний запуск без Docker: SQLite-файл, кеш і пошта в пам'яті/консолі.

    $env:DJANGO_SETTINGS_MODULE = "bookstore.settings_local"
    python manage.py migrate
"""

from .settings import *  # noqa: F401,F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if "debug_toolbar" not in m]  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_local.sqlite3",  # noqa: F405
    }
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
