"""Клас замовлення."""

from product import Product


class Order:
    """Замовлення: список товарів і загальна сума."""

    def __init__(self) -> None:
        self.products: list[Product] = []
        self.total_amount: float = 0.0

    def add_product(self, product: Product, quantity: int = 1) -> None:
        """Додає товар до замовлення і списує його зі складу."""
        if quantity <= 0:
            raise ValueError("Кількість має бути додатною.")
        if product.stock < quantity:
            raise ValueError(
                f"Недостатньо товару «{product.name}»: є {product.stock}, потрібно {quantity}."
            )
        product.change_stock(product.stock - quantity)
        self.products.extend([product] * quantity)
        self.calculate_total()

    def calculate_total(self) -> float:
        """Рахує суму замовлення."""
        self.total_amount = sum(item.price for item in self.products)
        return self.total_amount

    def __str__(self) -> str:
        if not self.products:
            return "Порожнє замовлення (0.00 грн)"
        self.calculate_total()
        grouped: dict[int, tuple[Product, int]] = {}
        for item in self.products:
            product, count = grouped.get(id(item), (item, 0))
            grouped[id(item)] = (product, count + 1)
        lines = ["Замовлення:"]
        for product, count in grouped.values():
            lines.append(f"  - {product.name} x {count} = {product.price * count:.2f} грн")
        return "\n".join(lines + [f"Разом: {self.total_amount:.2f} грн"])
