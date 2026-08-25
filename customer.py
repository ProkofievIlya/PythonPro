"""Клас клієнта магазину."""

from __future__ import annotations

from order import Order


class Customer:
    """Клієнт магазину.

    Attributes:
        name: Ім'я клієнта.
        email: Електронна пошта.
        orders: Список замовлень клієнта.
    """

    def __init__(self, name: str, email: str) -> None:
        """Створює клієнта без замовлень.

        Args:
            name: Ім'я клієнта.
            email: Електронна пошта.

        Raises:
            ValueError: Якщо ім'я порожнє або email некоректний.
        """
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Ім'я клієнта не може бути порожнім.")

        cleaned_email = email.strip().casefold()
        if "@" not in cleaned_email or cleaned_email.startswith("@") or cleaned_email.endswith("@"):
            raise ValueError(f"Некоректна електронна пошта: {email!r}.")

        self.name: str = cleaned_name
        self.email: str = cleaned_email
        self.orders: list[Order] = []

    def add_order(self, order: Order) -> None:
        """Додає нове замовлення до списку клієнта.

        Args:
            order: Замовлення, у якому вже є хоча б один товар.

        Raises:
            ValueError: Якщо замовлення порожнє.
        """
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

    def __repr__(self) -> str:
        return (
            f"Customer(name={self.name!r}, email={self.email!r}, "
            f"orders={len(self.orders)})"
        )
