from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Конфігурація додатку catalog."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "Каталог"
