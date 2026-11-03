from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = gettext_lazy("Каталог")
