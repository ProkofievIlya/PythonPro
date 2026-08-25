"""Клас клієнта магазину."""

from order import Order


class Customer:
    """Клієнт: ім'я, email, список замовлень."""

    def __init__(self, name: str, email: str) -> None:
        email = email.strip().lower()
        if not name.strip() or "@" not in email or email[0] == "@" or email[-1] == "@":
            raise ValueError("Некоректні дані клієнта.")
        self.name, self.email = name.strip(), email
        self.orders: list[Order] = []

    def add_order(self, order: Order) -> None:
        """Додає нове замовлення клієнту."""
        if not order.products:
            raise ValueError("Не можна додати порожнє замовлення.")
        order.calculate_total()
        self.orders.append(order)

    def __str__(self) -> str:
        spent = sum(order.total_amount for order in self.orders)
        return (
            f"{self.name} <{self.email}> — замовлень: {len(self.orders)}, "
            f"витрачено: {spent:.2f} грн"
        )
