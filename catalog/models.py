from functools import lru_cache
from typing import Any

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.db import models
from django.utils.text import slugify
from django.utils.translation import get_language, gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


COVER_PLACEHOLDER = "img/books/placeholder.svg"


def _is_english() -> bool:
    return (get_language() or "").startswith("en")


@lru_cache(maxsize=512)
def _static_exists(path: str) -> bool:
    return finders.find(path) is not None


class Category(models.Model):
    name = models.CharField(pgettext_lazy("category name", "Назва"), max_length=200)
    slug = models.SlugField(_("Slug"), max_length=200, unique=True)
    name_en = models.CharField(
        _("Назва категорії (англійською)"), max_length=200, blank=True, default=""
    )

    class Meta:
        verbose_name = _("Категорія")
        verbose_name_plural = _("Категорії")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def localized_name(self) -> str:
        """Назва мовою інтерфейсу (англійська, якщо заповнена, інакше основна)."""
        return (self.name_en if _is_english() else "") or self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Book(models.Model):
    title = models.CharField(pgettext_lazy("book title", "Назва"), max_length=255)
    author = models.CharField(_("Автор"), max_length=255)
    price = models.DecimalField(_("Ціна"), max_digits=10, decimal_places=2)
    description = models.TextField(_("Опис"), blank=True)
    stock = models.PositiveIntegerField(_("Залишок"), default=0)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="books",
        verbose_name=_("Категорія"),
    )
    title_en = models.CharField(
        _("Назва (англійською)"), max_length=255, blank=True, default=""
    )
    author_en = models.CharField(
        _("Автор (англійською)"), max_length=255, blank=True, default=""
    )
    description_en = models.TextField(_("Опис (англійською)"), blank=True, default="")
    cover = models.ImageField(_("Обкладинка"), upload_to="covers/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Книга")
        verbose_name_plural = _("Книги")
        ordering = ["title"]

    def __str__(self) -> str:
        return f"{self.title} — {self.author}"

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def cover_url(self) -> str:
        """Завантажена обкладинка -> демо-обкладинка static/img/books/<id>.jpg -> заглушка."""
        if self.cover:
            return self.cover.url
        demo = f"img/books/{self.pk}.jpg"
        if self.pk and _static_exists(demo):
            return static(demo)
        return static(COVER_PLACEHOLDER)

    @property
    def localized_title(self) -> str:
        return (self.title_en if _is_english() else "") or self.title

    @property
    def localized_author(self) -> str:
        return (self.author_en if _is_english() else "") or self.author

    @property
    def localized_description(self) -> str:
        return (self.description_en if _is_english() else "") or self.description


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Очікує оплату")
        PAID = "paid", _("Оплачено")
        CANCELLED = "cancelled", _("Скасовано")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("Користувач"),
    )
    email = models.EmailField(_("Email"))
    status = models.CharField(
        _("Статус"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total = models.DecimalField(_("Сума"), max_digits=10, decimal_places=2, default=0)
    stripe_session_id = models.CharField(
        _("Stripe session"),
        max_length=255,
        blank=True,
        unique=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Замовлення")
        verbose_name_plural = pgettext_lazy("plural", "Замовлення")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return gettext("Замовлення #%(pk)s") % {"pk": self.pk}


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Замовлення"),
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("Книга"),
    )
    price = models.DecimalField(_("Ціна"), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_("Кількість"), default=1)

    class Meta:
        verbose_name = _("Позиція замовлення")
        verbose_name_plural = _("Позиції замовлення")

    def __str__(self) -> str:
        return f"{self.book} × {self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity
