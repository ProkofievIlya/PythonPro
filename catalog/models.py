from typing import Any

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField("Назва", max_length=200)
    slug = models.SlugField("Slug", max_length=200, unique=True)

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Book(models.Model):
    title = models.CharField("Назва", max_length=255)
    author = models.CharField("Автор", max_length=255)
    price = models.DecimalField("Ціна", max_digits=10, decimal_places=2)
    description = models.TextField("Опис", blank=True)
    stock = models.PositiveIntegerField("Залишок", default=0)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="books",
        verbose_name="Категорія",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ["title"]

    def __str__(self) -> str:
        return f"{self.title} — {self.author}"

    @property
    def in_stock(self) -> bool:
        return self.stock > 0


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Очікує оплату"
        PAID = "paid", "Оплачено"
        CANCELLED = "cancelled", "Скасовано"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Користувач",
    )
    email = models.EmailField("Email")
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total = models.DecimalField("Сума", max_digits=10, decimal_places=2, default=0)
    stripe_session_id = models.CharField(
        "Stripe session",
        max_length=255,
        blank=True,
        unique=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Замовлення"
        verbose_name_plural = "Замовлення"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Замовлення #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Замовлення",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Книга",
    )
    price = models.DecimalField("Ціна", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("Кількість", default=1)

    class Meta:
        verbose_name = "Позиція замовлення"
        verbose_name_plural = "Позиції замовлення"

    def __str__(self) -> str:
        return f"{self.book} × {self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity
