"""Клас товару магазину."""


class Product:
    """Товар: назва, категорія, ціна, кількість на складі."""

    def __init__(self, name: str, category: str, price: float, stock: int) -> None:
        if not name.strip() or not category.strip() or price < 0 or stock < 0:
            raise ValueError("Некоректні дані товару.")
        self.name, self.category = name.strip(), category.strip()
        self.price, self.stock = float(price), int(stock)

    def change_price(self, new_price: float) -> None:
        """Змінює ціну товару."""
        if new_price < 0:
            raise ValueError("Ціна не може бути від'ємною.")
        self.price = float(new_price)

    def change_stock(self, new_quantity: int) -> None:
        """Змінює кількість на складі."""
        if new_quantity < 0:
            raise ValueError("Кількість не може бути від'ємною.")
        self.stock = int(new_quantity)

    def __str__(self) -> str:
        return f"{self.name} [{self.category}] — {self.price:.2f} грн, на складі: {self.stock} шт."
