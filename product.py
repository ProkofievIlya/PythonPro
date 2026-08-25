"""Клас товару магазину."""


class Product:
    """Товар: назва, категорія, ціна, кількість на складі."""

    def __init__(
        self, name: str, category: str, price: float, stock: int
    ) -> None:
        """Створює товар із перевіркою назви, ціни та кількості."""
        self.name = name
        self.category = category
        self.price = price
        self.stock = stock

    @property
    def name(self) -> str:
        """Назва товару."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        text = value.strip()
        if not text:
            raise ValueError("Назва товару не може бути порожньою.")
        self._name = text

    @property
    def category(self) -> str:
        """Категорія товару."""
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        text = value.strip()
        if not text:
            raise ValueError("Категорія не може бути порожньою.")
        self._category = text

    @property
    def price(self) -> float:
        """Ціна однієї одиниці."""
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        number = float(value)
        if number < 0:
            raise ValueError("Ціна не може бути від'ємною.")
        self._price = number

    @property
    def stock(self) -> int:
        """Кількість на складі."""
        return self._stock

    @stock.setter
    def stock(self, value: int) -> None:
        number = int(value)
        if number < 0:
            raise ValueError("Кількість не може бути від'ємною.")
        self._stock = number

    def change_price(self, new_price: float) -> None:
        """Змінює ціну товару."""
        self.price = new_price

    def change_stock(self, new_quantity: int) -> None:
        """Змінює кількість на складі."""
        self.stock = new_quantity

    def __str__(self) -> str:
        """Повертає рядок із назвою, ціною та залишком."""
        return (
            f"{self.name} [{self.category}] — {self.price:.2f} грн, "
            f"на складі: {self.stock} шт."
        )
