from typing import Any

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
