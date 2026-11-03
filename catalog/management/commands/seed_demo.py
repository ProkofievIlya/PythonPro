from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Book, Category


EN_CATEGORIES = {
    "hudozhnya-literatura": "Fiction",
    "naukova-literatura": "Science",
    "dytiacha-literatura": "Children's books",
}

# назва (укр.) -> (title_en, author_en, description_en)
EN_BOOKS = {
    "Кобзар": ("Kobzar", "Taras Shevchenko", "A collection of poems by the Ukrainian classic."),
    "Коротка історія часу": ("A Brief History of Time", "Stephen Hawking", "A popular science book about the Universe."),
    "Гаррі Поттер і філософський камінь": ("Harry Potter and the Philosopher's Stone", "J.K. Rowling", "The first book in the series about a young wizard."),
    "Зачарована Десна": ("The Enchanted Desna", "Lina Kostenko", "A poetry collection by a contemporary Ukrainian poet."),
    "Тигролов": ("The Tiger Hunters", "Ivan Bahrianyi", "An adventure novel about escape and life in the taiga."),
    "Людина розумна. Коротка історія людства": ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "A survey of human history from the Stone Age to the present day."),
    "Астрофізика з гумором": ("Astrophysics with Humor", "Neil deGrasse Tyson", "An easy introduction to space and the physics of stars."),
    "Маленький принц": ("The Little Prince", "Antoine de Saint-Exupery", "A fairy tale about friendship, responsibility and growing up."),
    "Кайдашева сім'я": ("The Kaidash Family", "Ivan Nechuy-Levytsky", "A novel about a Ukrainian family and the quarrels between a mother-in-law and her daughters-in-law."),
    "Енеїда": ("Eneida", "Ivan Kotliarevsky", "A comic poem that launched modern Ukrainian literature."),
    "Коротка історія майже всього": ("A Short History of Nearly Everything", "Bill Bryson", "A lively account of science, from the Big Bang to the emergence of humans."),
    "Аліса в Країні Див": ("Alice in Wonderland", "Lewis Carroll", "A fairy tale about a girl who finds herself in a world of strange creatures and riddles."),
}


class Command(BaseCommand):
    help = "Додає 3 категорії та демо-книги з англійськими назвами (get_or_create)."

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
            Category.objects.filter(pk=category.pk).update(
                name_en=EN_CATEGORIES.get(slug, "")
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
            title_en, author_en, description_en = EN_BOOKS.get(title, ("", "", ""))
            Book.objects.filter(pk=book.pk).update(
                title_en=title_en,
                author_en=author_en,
                description_en=description_en,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Книга: {title}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Категорій: {Category.objects.count()}, "
                f"книг: {Book.objects.count()}"
            )
        )
