from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    phone = models.CharField(_("Телефон"), max_length=20, blank=True)

    class Meta:
        verbose_name = _("Користувач")
        verbose_name_plural = _("Користувачі")

    def __str__(self) -> str:
        return self.username
