"""Магазин: зчитування стану з файлу та взаємодія класів."""

from __future__ import annotations

from pathlib import Path

from customer import Customer
from order import Order
from product import Product

FIELD_SEPARATOR = "|"
PRODUCT_HEADERS = {"назва", "name"}
CUSTOMER_HEADERS = {"ім'я", "имя", "імя", "name"}


class Shop:
    """Магазин: каталог товарів і база клієнтів.

    Початковий стан зчитується з текстового файлу::

        [products]
        Назва|Категорія|Ціна|Кількість
        Намет Storm-2|намети|4290.00|7

        [customers]
        Ім'я|Email
        Соломія Гнатюк|solomiya.hnatiuk@mail.ua

    Рядки з ``#`` — коментарі.

    Attributes:
        products: Товари магазину.
        customers: Клієнти магазину.
    """

    def __init__(self) -> None:
        """Створює порожній магазин."""
        self.products: list[Product] = []
        self.customers: list[Customer] = []

    @classmethod
    def from_file(cls, path: str | Path) -> Shop:
        """Створює магазин зі стану, записаного у файлі.

        Args:
            path: Шлях до ``.txt`` із секціями ``[products]`` і ``[customers]``.

        Returns:
            Заповнений магазин.

        Raises:
            FileNotFoundError: Якщо файл не існує.
            ValueError: Якщо формат рядка некоректний.
        """
        shop = cls()
        shop.load_from_file(path)
        return shop

    def load_from_file(self, path: str | Path) -> None:
        """Завантажує товари та клієнтів із файлу.

        Args:
            path: Шлях до текстового файлу стану.

        Raises:
            FileNotFoundError: Якщо файл не знайдено.
            ValueError: Якщо рядок має хибний формат.
        """
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Файл стану магазину не знайдено: {file_path}")

        products: list[Product] = []
        customers: list[Customer] = []
        section: str | None = None

        for line_number, raw_line in enumerate(
            file_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            marker = line.casefold()
            if marker == "[products]":
                section = "products"
                continue
            if marker == "[customers]":
                section = "customers"
                continue
            if section is None:
                raise ValueError(
                    f"Рядок {line_number}: дані поза секціями [products]/[customers]."
                )
            if self._is_header(line, section):
                continue

            parts = [part.strip() for part in line.split(FIELD_SEPARATOR)]
            try:
                if section == "products":
                    products.append(self._parse_product(parts))
                else:
                    customers.append(self._parse_customer(parts))
            except ValueError as error:
                raise ValueError(f"Рядок {line_number}: {error}") from error

        self.products = products
        self.customers = customers

    def save_to_file(self, path: str | Path) -> None:
        """Зберігає поточні товари та клієнтів у текстовий файл.

        Args:
            path: Файл, який буде створено або перезаписано.
        """
        rows = [
            "# Стан магазину",
            "[products]",
            "Назва|Категорія|Ціна|Кількість",
        ]
        rows.extend(
            f"{item.name}{FIELD_SEPARATOR}{item.category}"
            f"{FIELD_SEPARATOR}{item.price:.2f}{FIELD_SEPARATOR}{item.stock}"
            for item in self.products
        )
        rows.extend(["", "[customers]", "Ім'я|Email"])
        rows.extend(
            f"{person.name}{FIELD_SEPARATOR}{person.email}"
            for person in self.customers
        )
        Path(path).write_text("\n".join(rows) + "\n", encoding="utf-8")

    def find_product(self, name: str) -> Product | None:
        """Шукає товар за назвою (без урахування регістру)."""
        needle = name.strip().casefold()
        return next(
            (item for item in self.products if item.name.casefold() == needle),
            None,
        )

    def find_customer(self, email: str) -> Customer | None:
        """Шукає клієнта за електронною поштою."""
        needle = email.strip().casefold()
        return next(
            (person for person in self.customers if person.email == needle),
            None,
        )

    def add_product(self, product: Product) -> None:
        """Додає товар до каталогу.

        Raises:
            ValueError: Якщо товар із такою назвою вже є.
        """
        if self.find_product(product.name) is not None:
            raise ValueError(f"Товар «{product.name}» уже є в каталозі.")
        self.products.append(product)

    def add_customer(self, customer: Customer) -> None:
        """Додає клієнта до бази магазину.

        Raises:
            ValueError: Якщо клієнт із такою поштою вже є.
        """
        if self.find_customer(customer.email) is not None:
            raise ValueError(f"Клієнт із поштою {customer.email} уже зареєстрований.")
        self.customers.append(customer)

    def create_order(
        self, customer: Customer, items: list[tuple[Product, int]]
    ) -> Order:
        """Створює замовлення, списує товар зі складу і додає його клієнту.

        Якщо додати якусь позицію не вдалося, раніше списані одиниці
        повертаються на склад.

        Args:
            customer: Клієнт магазину.
            items: Пари ``(товар, кількість)``.

        Returns:
            Створене замовлення.

        Raises:
            ValueError: Якщо клієнт або товар не з цього магазину,
                список порожній чи не вистачає залишку.
        """
        if customer not in self.customers:
            raise ValueError("Клієнт не зареєстрований у цьому магазині.")
        if not items:
            raise ValueError("Замовлення має містити хоча б один товар.")

        order = Order()
        try:
            for product, quantity in items:
                if product not in self.products:
                    raise ValueError(
                        f"Товар «{product.name}» не належить цьому магазину."
                    )
                order.add_product(product, quantity)
        except ValueError:
            for sold in order.products:
                sold.change_stock(sold.stock + 1)
            raise

        customer.add_order(order)
        return order

    @staticmethod
    def _is_header(line: str, section: str) -> bool:
        """True, якщо рядок — заголовок таблиці, а не дані."""
        first = (
            line.split(FIELD_SEPARATOR, 1)[0]
            .strip()
            .casefold()
            .replace("’", "'")
            .replace("ʼ", "'")
        )
        headers = PRODUCT_HEADERS if section == "products" else CUSTOMER_HEADERS
        return first in headers

    @staticmethod
    def _parse_product(parts: list[str]) -> Product:
        """Перетворює поля рядка файлу на :class:`Product`."""
        if len(parts) != 4:
            raise ValueError(
                f"очікується 4 поля (назва|категорія|ціна|кількість), отримано {len(parts)}."
            )
        name, category, price_raw, stock_raw = parts
        try:
            price = float(price_raw.replace(",", "."))
            stock = int(stock_raw)
        except ValueError as error:
            raise ValueError("ціна має бути числом, кількість — цілим числом.") from error
        return Product(name=name, category=category, price=price, stock=stock)

    @staticmethod
    def _parse_customer(parts: list[str]) -> Customer:
        """Перетворює поля рядка файлу на :class:`Customer`."""
        if len(parts) != 2:
            raise ValueError(f"очікується 2 поля (ім'я|email), отримано {len(parts)}.")
        name, email = parts
        return Customer(name=name, email=email)
