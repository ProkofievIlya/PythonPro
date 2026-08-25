"""Консольна система управління магазином.

Завантажує товари та клієнтів із текстового файлу і дає змогу
змінювати ціни, залишки та оформлювати замовлення.
"""

from __future__ import annotations

import sys
from pathlib import Path

from customer import Customer
from product import Product
from shop import Shop

DATA_FILE = Path(__file__).resolve().parent / "data" / "shop_initial.txt"


def _read_line(prompt: str) -> str:
    """Зчитує рядок з консолі без зайвих пробілів."""
    return input(prompt).strip()


def _read_float(prompt: str) -> float:
    """Зчитує невід'ємне дробове число."""
    raw = _read_line(prompt)
    try:
        value = float(raw.replace(",", "."))
    except ValueError as error:
        raise ValueError("Потрібно ввести число.") from error
    if value < 0:
        raise ValueError("Число не може бути від'ємним.")
    return value


def _read_int(prompt: str) -> int:
    """Зчитує невід'ємне ціле число."""
    raw = _read_line(prompt)
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("Потрібно ввести ціле число.") from error
    if value < 0:
        raise ValueError("Число не може бути від'ємним.")
    return value


def _ask_product(shop: Shop, prompt: str = "Назва товару: ") -> Product | None:
    """Просить назву і повертає товар або ``None``, якщо не знайдено."""
    product = shop.find_product(_read_line(prompt))
    if product is None:
        print("Товар не знайдено.")
    return product


def _ask_customer(shop: Shop) -> Customer | None:
    """Просить email і повертає клієнта або ``None``, якщо не знайдено."""
    customer = shop.find_customer(_read_line("Email клієнта: "))
    if customer is None:
        print("Клієнта не знайдено.")
    return customer


def show_products(shop: Shop) -> None:
    """Виводить каталог товарів."""
    print("\n=== Товари ===")
    if not shop.products:
        print("Каталог порожній.")
        return
    for index, product in enumerate(shop.products, start=1):
        print(f"{index}. {product}")


def show_customers(shop: Shop) -> None:
    """Виводить список клієнтів."""
    print("\n=== Клієнти ===")
    if not shop.customers:
        print("Клієнтів ще немає.")
        return
    for index, customer in enumerate(shop.customers, start=1):
        print(f"{index}. {customer}")


def change_product_price(shop: Shop) -> None:
    """Змінює ціну вибраного товару."""
    show_products(shop)
    product = _ask_product(shop)
    if product is None:
        return
    product.change_price(_read_float("Нова ціна: "))
    print(f"Ціну оновлено: {product}")


def change_product_stock(shop: Shop) -> None:
    """Змінює кількість товару на складі."""
    show_products(shop)
    product = _ask_product(shop)
    if product is None:
        return
    product.change_stock(_read_int("Нова кількість на складі: "))
    print(f"Залишок оновлено: {product}")


def add_new_product(shop: Shop) -> None:
    """Додає новий товар до каталогу."""
    shop.add_product(
        Product(
            name=_read_line("Назва: "),
            category=_read_line("Категорія: "),
            price=_read_float("Ціна: "),
            stock=_read_int("Кількість на складі: "),
        )
    )
    print("Товар додано.")


def add_new_customer(shop: Shop) -> None:
    """Реєструє нового клієнта."""
    shop.add_customer(
        Customer(name=_read_line("Ім'я: "), email=_read_line("Email: "))
    )
    print("Клієнта зареєстровано.")


def place_order(shop: Shop) -> None:
    """Оформлює нове замовлення для вибраного клієнта."""
    show_customers(shop)
    customer = _ask_customer(shop)
    if customer is None:
        return

    show_products(shop)
    items: list[tuple[Product, int]] = []
    print("Додавайте товари. Порожня назва — завершити набір.")
    while True:
        name = _read_line("Назва товару (Enter — готово): ")
        if not name:
            break
        product = shop.find_product(name)
        if product is None:
            print("Товар не знайдено, спробуйте ще раз.")
            continue
        quantity = _read_int("Кількість: ")
        items.append((product, quantity))
        print(f"  додано: {product.name} x {quantity}")

    if not items:
        print("Замовлення скасовано: не додано жодного товару.")
        return

    order = shop.create_order(customer, items)
    print("\nЗамовлення оформлено.")
    print(order)


def show_customer_orders(shop: Shop) -> None:
    """Показує всі замовлення вибраного клієнта."""
    show_customers(shop)
    customer = _ask_customer(shop)
    if customer is None:
        return

    print(f"\n=== Замовлення: {customer.name} ===")
    if not customer.orders:
        print("Замовлень немає.")
        return
    for index, order in enumerate(customer.orders, start=1):
        print(f"\n№{index}")
        print(order)


def save_shop(shop: Shop) -> None:
    """Зберігає поточний стан каталогу та клієнтів у файл."""
    shop.save_to_file(DATA_FILE)
    print(f"Стан збережено у файл: {DATA_FILE}")


def print_menu() -> None:
    """Друкує головне меню."""
    print("\n======== Магазин ========")
    print("1. Показати товари")
    print("2. Показати клієнтів")
    print("3. Змінити ціну товару")
    print("4. Змінити кількість на складі")
    print("5. Додати товар")
    print("6. Додати клієнта")
    print("7. Оформити замовлення")
    print("8. Показати замовлення клієнта")
    print("9. Зберегти стан у файл")
    print("0. Вихід")


def _configure_console() -> None:
    """Вмикає UTF-8 у консолі Windows, якщо це можливо."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
    except (OSError, ValueError, AttributeError):
        pass


def run() -> None:
    """Головний цикл програми."""
    _configure_console()
    print("Завантаження початкового стану магазину...")
    try:
        shop = Shop.from_file(DATA_FILE)
    except FileNotFoundError as error:
        print(f"Не вдалося відкрити файл стану: {error}")
        return
    except ValueError as error:
        print(f"Файл стану має некоректний формат: {error}")
        return

    print(
        f"Завантажено товарів: {len(shop.products)}, "
        f"клієнтів: {len(shop.customers)}."
    )

    actions = {
        "1": show_products,
        "2": show_customers,
        "3": change_product_price,
        "4": change_product_stock,
        "5": add_new_product,
        "6": add_new_customer,
        "7": place_order,
        "8": show_customer_orders,
        "9": save_shop,
    }

    while True:
        print_menu()
        choice = _read_line("Оберіть пункт: ")
        if choice == "0":
            print("До побачення.")
            break
        action = actions.get(choice)
        if action is None:
            print("Невідомий пункт меню.")
            continue
        try:
            action(shop)
        except ValueError as error:
            print(f"Помилка: {error}")
        except KeyboardInterrupt:
            print("\nОперацію скасовано.")


if __name__ == "__main__":
    run()
