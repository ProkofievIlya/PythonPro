"""Магазин: зчитування стану з файлу та взаємодія класів."""

from pathlib import Path

from customer import Customer
from order import Order
from product import Product


class Shop:
    """Магазин. Створюється зі стану у txt (секції [products] і [customers])."""

    def __init__(self) -> None:
        self.products: list[Product] = []
        self.customers: list[Customer] = []

    @classmethod
    def from_file(cls, path: str | Path) -> "Shop":
        """Створює магазин зі стану у файлі."""
        shop = cls()
        shop.load_from_file(path)
        return shop

    def load_from_file(self, path: str | Path) -> None:
        """Читає товари та клієнтів з файлу."""
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Файл не знайдено: {file_path}")
        self.products, self.customers, section = [], [], ""
        for raw in file_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            low = line.lower()
            if low in {"[products]", "[customers]"}:
                section = low[1:-1]
                continue
            parts = [part.strip() for part in line.split("|")]
            first = parts[0].lower().replace("’", "'").replace("ʼ", "'")
            if first in {"назва", "ім'я", "имя", "імя"}:
                continue
            if section not in {"products", "customers"}:
                raise ValueError(f"Дані поза секціями: {line}")
            try:
                if section == "products":
                    name, category, price, stock = parts
                    self.products.append(
                        Product(name, category, float(price.replace(",", ".")), int(stock))
                    )
                else:
                    self.customers.append(Customer(parts[0], parts[1]))
            except (ValueError, TypeError) as error:
                raise ValueError(f"Некоректний рядок: {line}") from error

    def save_to_file(self, path: str | Path) -> None:
        """Зберігає товари та клієнтів у файл."""
        rows = ["# Стан магазину", "[products]", "Назва|Категорія|Ціна|Кількість"]
        rows += [f"{p.name}|{p.category}|{p.price:.2f}|{p.stock}" for p in self.products]
        rows += ["", "[customers]", "Ім'я|Email"]
        rows += [f"{c.name}|{c.email}" for c in self.customers]
        Path(path).write_text("\n".join(rows) + "\n", encoding="utf-8")

    def find_product(self, name: str) -> Product | None:
        name = name.strip().lower()
        return next((p for p in self.products if p.name.lower() == name), None)

    def find_customer(self, email: str) -> Customer | None:
        email = email.strip().lower()
        return next((c for c in self.customers if c.email == email), None)

    def add_product(self, product: Product) -> None:
        if self.find_product(product.name):
            raise ValueError(f"Товар «{product.name}» уже є в каталозі.")
        self.products.append(product)

    def add_customer(self, customer: Customer) -> None:
        if self.find_customer(customer.email):
            raise ValueError(f"Клієнт із поштою {customer.email} уже зареєстрований.")
        self.customers.append(customer)

    def create_order(self, customer: Customer, items: list[tuple[Product, int]]) -> Order:
        """Оформлює замовлення. При помилці склад відкочується."""
        if customer not in self.customers or not items:
            raise ValueError("Потрібні зареєстрований клієнт і хоча б один товар.")
        order = Order()
        try:
            for product, quantity in items:
                if product not in self.products:
                    raise ValueError(f"Товар «{product.name}» не належить цьому магазину.")
                order.add_product(product, quantity)
        except ValueError:
            for sold in order.products:
                sold.change_stock(sold.stock + 1)
            raise
        customer.add_order(order)
        return order
