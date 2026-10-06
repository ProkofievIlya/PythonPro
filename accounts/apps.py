from django.apps import AppConfig
from django.db.models.signals import post_migrate


def ensure_local_site(sender, **kwargs):
    from django.contrib.sites.models import Site
    from django.db.utils import OperationalError, ProgrammingError

    try:
        site, _ = Site.objects.get_or_create(
            id=1,
            defaults={"domain": "127.0.0.1:8000", "name": "Bookstore"},
        )
    except (OperationalError, ProgrammingError):
        return
    if site.domain == "example.com":
        site.domain = "127.0.0.1:8000"
        site.name = "Bookstore"
        site.save(update_fields=["domain", "name"])


def ensure_catalog_groups(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission

    manager_codes = ("add_book", "change_book", "delete_book", "view_book")
    viewer_codes = ("view_book",)
    manager_perms = Permission.objects.filter(
        content_type__app_label="catalog",
        codename__in=manager_codes,
    )
    if manager_perms.count() < len(manager_codes):
        return

    managers, _ = Group.objects.get_or_create(name="Менеджери каталогу")
    managers.permissions.set(manager_perms)

    viewers, _ = Group.objects.get_or_create(name="Переглядачі")
    viewers.permissions.set(
        Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=viewer_codes,
        )
    )


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Користувачі"

    def ready(self) -> None:
        post_migrate.connect(
            ensure_catalog_groups,
            dispatch_uid="accounts.ensure_catalog_groups",
        )
        post_migrate.connect(
            ensure_local_site,
            dispatch_uid="accounts.ensure_local_site",
        )
