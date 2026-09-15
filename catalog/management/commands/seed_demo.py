from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Book, Category


class Command(BaseCommand):
    help = "Додає 3 категорії та 3 книги (get_or_create)."

    def handle(self, *args, **options) -> None:
        categories_data = [
            ("Художня література", "hudozhnya-literatura"),
            ("Наукова література", "naukova-literatura"),
            ("Дитяча література", "dytiacha-literatura"),
        ]
        categories: list[Category] = []
        for name, slug in categories_data:
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name},
            )
            categories.append(category)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Категорія: {name}"))

        books_data = [
            (
                "Кобзар",
                "Тарас Шевченко",
                Decimal("199.00"),
                "Збірка поезій українського класика.",
                12,
                categories[0],
            ),
            (
                "Коротка історія часу",
                "Стівен Гокінг",
                Decimal("350.00"),
                "Популярна наукова книга про Всесвіт.",
                8,
                categories[1],
            ),
            (
                "Гаррі Поттер і філософський камінь",
                "Дж. К. Роулінг",
                Decimal("299.00"),
                "Перша книга серії про юного чарівника.",
                25,
                categories[2],
            ),
        ]
        for title, author, price, description, stock, category in books_data:
            book, created = Book.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    "price": price,
                    "description": description,
                    "stock": stock,
                    "category": category,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Книга: {title}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Категорій: {Category.objects.count()}, "
                f"книг: {Book.objects.count()}"
            )
        )
