from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Book, Category


class Command(BaseCommand):
    help = "Додає 3 категорії та демо-книги (get_or_create)."

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
                "Джоан Ролінґ",
                Decimal("299.00"),
                "Перша книга серії про юного чарівника.",
                25,
                categories[2],
            ),
            (
                "Зачарована Десна",
                "Ліна Костенко",
                Decimal("220.00"),
                "Поетична збірка сучасної української поетеси.",
                15,
                categories[0],
            ),
            (
                "Тигролов",
                "Іван Багряний",
                Decimal("265.00"),
                "Пригодницький роман про втечу та життя в тайзі.",
                11,
                categories[0],
            ),
            (
                "Людина розумна. Коротка історія людства",
                "Ювал Ной Гарарі",
                Decimal("420.00"),
                "Огляд історії людства від кам’яного віку до сьогодення.",
                6,
                categories[1],
            ),
            (
                "Астрофізика з гумором",
                "Ніл Деграсс Тайсон",
                Decimal("310.00"),
                "Легке введення в космос і фізику зірок.",
                9,
                categories[1],
            ),
            (
                "Маленький принц",
                "Антуан де Сент-Екзюпері",
                Decimal("180.00"),
                "Казка про дружбу, відповідальність і дорослішання.",
                30,
                categories[2],
            ),
            (
                "Кайдашева сім'я",
                "Іван Нечуй-Левицький",
                Decimal("210.00"),
                "Повість про життя української родини та сварки між свекрухою і невістками.",
                14,
                categories[0],
            ),
            (
                "Енеїда",
                "Іван Котляревський",
                Decimal("230.00"),
                "Жартівлива поема, з якої почалася нова українська література.",
                10,
                categories[0],
            ),
            (
                "Коротка історія майже всього",
                "Білл Брайсон",
                Decimal("390.00"),
                "Жвава розповідь про науку: від Великого вибуху до появи людини.",
                7,
                categories[1],
            ),
            (
                "Аліса в Країні Див",
                "Льюїс Керрол",
                Decimal("250.00"),
                "Казка про дівчинку, яка потрапляє у світ дивних створінь і загадок.",
                18,
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
