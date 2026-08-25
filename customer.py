"""Клас клієнта магазину."""

from order import Order


class Customer:
    """Клієнт: ім'я, email, список замовлень."""

    def __init__(self, name: str, email: str) -> None:
        """Створює клієнта без замовлень."""
        self.name = name
        self.email = email
        self.orders: list[Order] = []

    @property
    def name(self) -> str:
        """Ім'я клієнта."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        text = value.strip()
        if not text:
            raise ValueError("Ім'я клієнта не може бути порожнім.")
        self._name = text

    @property
    def email(self) -> str:
        """Електронна пошта клієнта."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        email = value.strip().lower()
        if email.count("@") != 1:
            raise ValueError("Некоректні дані клієнта.")
        local, domain = email.split("@")
        if (
            not local
            or not domain
            or "." not in domain
            or domain[0] == "."
            or domain[-1] == "."
        ):
            raise ValueError("Некоректні дані клієнта.")
        self._email = email

    def add_order(self, order: Order) -> None:
        """Додає нове замовлення клієнту."""
        if not order.products:
            raise ValueError("Не можна додати порожнє замовлення.")
        order.calculate_total()
        self.orders.append(order)

    def __str__(self) -> str:
        """Повертає ім'я, email і статистику замовлень."""
        spent = sum(order.total_amount for order in self.orders)
        return (
            f"{self.name} <{self.email}> — замовлень: {len(self.orders)}, "
            f"витрачено: {spent:.2f} грн"
        )
