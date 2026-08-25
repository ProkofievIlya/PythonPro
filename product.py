"""Клас товару магазину."""

from __future__ import annotations


def _required_text(value: str, field_name: str) -> str:
    """Повертає текст без пробілів по краях або піднімає ValueError."""
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} не може бути порожнім.")
    return text


def _non_negative_float(value: float, field_name: str) -> float:
    """Перевіряє, що значення не від'ємне, і повертає його як float."""
    number = float(value)
    if number < 0:
        raise ValueError(f"{field_name} не може бути від'ємним.")
    return number


def _non_negative_int(value: int, field_name: str) -> int:
    """Перевіряє, що значення не від'ємне, і повертає його як int."""
    number = int(value)
    if number < 0:
        raise ValueError(f"{field_name} не може бути від'ємним.")
    return number


class Product:
    """Товар магазину.

    Attributes:
        name: Назва товару.
        category: Категорія (наприклад, ``"м'яка іграшка"``, ``"конструктор"``).
        price: Ціна однієї одиниці.
        stock: Кількість на складі.
    """

    def __init__(self, name: str, category: str, price: float, stock: int) -> None:
        """Створює товар із перевіркою вхідних даних.

        Args:
            name: Назва товару.
            category: Категорія товару.
            price: Початкова ціна (невід'ємна).
            stock: Початкова кількість на складі (невід'ємна).

        Raises:
            ValueError: Якщо назва чи категорія порожні або значення від'ємні.
        """
        self.name: str = _required_text(name, "Назва товару")
        self.category: str = _required_text(category, "Категорія товару")
        self.price: float = _non_negative_float(price, "Ціна")
        self.stock: int = _non_negative_int(stock, "Кількість на складі")

    def change_price(self, new_price: float) -> None:
        """Змінює ціну товару.

        Args:
            new_price: Нова невід'ємна ціна.

        Raises:
            ValueError: Якщо ціна від'ємна.
        """
        self.price = _non_negative_float(new_price, "Нова ціна")

    def change_stock(self, new_quantity: int) -> None:
        """Змінює кількість товару на складі.

        Args:
            new_quantity: Нова невід'ємна кількість.

        Raises:
            ValueError: Якщо кількість від'ємна.
        """
        self.stock = _non_negative_int(new_quantity, "Кількість на складі")

    def __str__(self) -> str:
        return (
            f"{self.name} [{self.category}] — {self.price:.2f} грн, "
            f"на складі: {self.stock} шт."
        )

    def __repr__(self) -> str:
        return (
            f"Product(name={self.name!r}, category={self.category!r}, "
            f"price={self.price!r}, stock={self.stock!r})"
        )
