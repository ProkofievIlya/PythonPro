"""Клас замовлення."""

from __future__ import annotations

from product import Product


class Order:
    """Замовлення клієнта.

    Attributes:
        products: Список товарів (кожна одиниця — окремий елемент).
        total_amount: Загальна сума замовлення.
    """

    def __init__(self) -> None:
        """Створює порожнє замовлення."""
        self.products: list[Product] = []
        self.total_amount: float = 0.0

    def add_product(self, product: Product, quantity: int = 1) -> None:
        """Додає товар до замовлення і списує відповідну кількість зі складу.

        Args:
            product: Товар, який додається.
            quantity: Кількість одиниць (за замовчуванням 1).

        Raises:
            ValueError: Якщо кількість не додатна або на складі недостатньо товару.
        """
        if quantity <= 0:
            raise ValueError("Кількість товару в замовленні має бути додатною.")
        if product.stock < quantity:
            raise ValueError(
                f"Недостатньо товару «{product.name}»: "
                f"є {product.stock}, потрібно {quantity}."
            )

        product.change_stock(product.stock - quantity)
        self.products.extend([product] * quantity)
        self.calculate_total()

    def calculate_total(self) -> float:
        """Обчислює загальну суму замовлення за цінами товарів у списку.

        Returns:
            Оновлена сума замовлення.
        """
        self.total_amount = sum(item.price for item in self.products)
        return self.total_amount

    def __str__(self) -> str:
        if not self.products:
            return "Порожнє замовлення (0.00 грн)"

        self.calculate_total()
        lines = ["Замовлення:"]
        for product, quantity in self._grouped_products():
            lines.append(
                f"  - {product.name} x {quantity} = "
                f"{product.price * quantity:.2f} грн"
            )
        lines.append(f"Разом: {self.total_amount:.2f} грн")
        return "\n".join(lines)

    def _grouped_products(self) -> list[tuple[Product, int]]:
        """Згортає повторювані одиниці в пари (товар, кількість)."""
        grouped: list[tuple[Product, int]] = []
        indexes: dict[int, int] = {}
        for item in self.products:
            key = id(item)
            if key not in indexes:
                indexes[key] = len(grouped)
                grouped.append((item, 0))
            product, count = grouped[indexes[key]]
            grouped[indexes[key]] = (product, count + 1)
        return grouped

    def __repr__(self) -> str:
        return (
            f"Order(products={len(self.products)} items, "
            f"total_amount={self.total_amount!r})"
        )
