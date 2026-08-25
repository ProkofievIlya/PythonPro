"""Клас замовлення."""

from product import Product


class Order:
    """Замовлення: список товарів і загальна сума."""

    def __init__(self) -> None:
        """Створює порожнє замовлення."""
        self.products: list[Product] = []
        self._unit_prices: list[float] = []

    @property
    def total_amount(self) -> float:
        """Загальна сума за зафіксованими цінами."""
        return sum(self._unit_prices)

    def add_product(self, product: Product, quantity: int = 1) -> None:
        """Додає товар до замовлення і списує його зі складу."""
        if quantity <= 0:
            raise ValueError("Кількість має бути додатною.")
        if product.stock < quantity:
            raise ValueError(
                f"Недостатньо товару «{product.name}»: "
                f"є {product.stock}, потрібно {quantity}."
            )
        unit_price = product.price
        product.change_stock(product.stock - quantity)
        self.products.extend([product] * quantity)
        self._unit_prices.extend([unit_price] * quantity)

    def restore_item(
        self, product: Product, quantity: int, unit_price: float
    ) -> None:
        """Відновлює позицію з файлу без зміни складу."""
        if quantity <= 0 or unit_price < 0:
            raise ValueError("Некоректна позиція замовлення.")
        self.products.extend([product] * quantity)
        self._unit_prices.extend([float(unit_price)] * quantity)

    def calculate_total(self) -> float:
        """Рахує суму замовлення."""
        return self.total_amount

    def grouped_lines(self) -> list[tuple[Product, int, float]]:
        """Повертає позиції (товар, кількість, ціна на момент купівлі)."""
        grouped: dict[tuple[int, float], tuple[Product, int]] = {}
        keys: list[tuple[int, float]] = []
        for item, unit in zip(self.products, self._unit_prices):
            key = (id(item), unit)
            if key not in grouped:
                keys.append(key)
                grouped[key] = (item, 0)
            product, count = grouped[key]
            grouped[key] = (product, count + 1)
        return [(grouped[key][0], grouped[key][1], key[1]) for key in keys]

    def __str__(self) -> str:
        """Повертає текст замовлення зі сумами позицій."""
        if not self.products:
            return "Порожнє замовлення (0.00 грн)"
        lines = ["Замовлення:"]
        for product, count, unit in self.grouped_lines():
            lines.append(
                f"  - {product.name} x {count} = "
                f"{unit * count:.2f} грн"
            )
        return "\n".join(
            lines + [f"Разом: {self.total_amount:.2f} грн"]
        )
