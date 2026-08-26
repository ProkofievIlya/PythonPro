"""Консольне меню магазину. Дані: data/shop_initial.txt."""

import sys
from pathlib import Path

from customer import Customer
from product import Product
from shop import Shop

DATA_FILE = Path(__file__).resolve().parent / "data" / "shop_initial.txt"


def ask(prompt: str) -> str:
    """Зчитує рядок з консолі."""
    return input(prompt).strip()


def ask_number(prompt: str, integer: bool = False) -> float | int:
    """Зчитує невід'ємне число (ціле або дробове)."""
    raw = ask(prompt).replace(",", ".")
    try:
        value = int(raw) if integer else float(raw)
    except ValueError as error:
        raise ValueError("Потрібно ввести число.") from error
    if value < 0:
        raise ValueError("Число не може бути від'ємним.")
    return value


def show_list(title: str, items: list, empty: str) -> None:
    """Друкує пронумерований список або повідомлення про порожнечу."""
    print(f"\n=== {title} ===")
    if not items:
        print(empty)
        return
    for i, item in enumerate(items, start=1):
        print(f"{i}. {item}")


def pick_product(shop: Shop) -> Product | None:
    """Просить назву товару і повертає його або None."""
    product = shop.find_product(ask("Назва товару: "))
    if not product:
        print("Товар не знайдено.")
    return product


def pick_customer(shop: Shop) -> Customer | None:
    """Просить email і повертає клієнта або None."""
    customer = shop.find_customer(ask("Email клієнта: "))
    if not customer:
        print("Клієнта не знайдено.")
    return customer


def show_products(shop: Shop) -> None:
    """Показує каталог товарів."""
    show_list("Товари", shop.products, "Каталог порожній.")


def show_customers(shop: Shop) -> None:
    """Показує список клієнтів."""
    show_list("Клієнти", shop.customers, "Клієнтів ще немає.")


def change_product_price(shop: Shop) -> None:
    """Змінює ціну вибраного товару."""
    show_products(shop)
    product = pick_product(shop)
    if product:
        product.change_price(ask_number("Нова ціна: "))
        print(f"Ціну оновлено: {product}")


def change_product_stock(shop: Shop) -> None:
    """Змінює кількість товару на складі."""
    show_products(shop)
    product = pick_product(shop)
    if product:
        product.change_stock(
            ask_number("Нова кількість на складі: ", integer=True)
        )
        print(f"Залишок оновлено: {product}")


def add_new_product(shop: Shop) -> None:
    """Додає новий товар у каталог."""
    shop.add_product(Product(
        ask("Назва: "),
        ask("Категорія: "),
        ask_number("Ціна: "),
        ask_number("Кількість на складі: ", integer=True),
    ))
    print("Товар додано.")


def add_new_customer(shop: Shop) -> None:
    """Реєструє нового клієнта."""
    shop.add_customer(Customer(ask("Ім'я: "), ask("Email: ")))
    print("Клієнта зареєстровано.")


def place_order(shop: Shop) -> None:
    """Оформлює замовлення для вибраного клієнта."""
    show_customers(shop)
    customer = pick_customer(shop)
    if not customer:
        return
    show_products(shop)
    items: list[tuple[Product, int]] = []
    print("Додавайте товари. Порожня назва — завершити набір.")
    while True:
        name = ask("Назва товару (Enter — готово): ")
        if not name:
            break
        product = shop.find_product(name)
        if not product:
            print("Товар не знайдено, спробуйте ще раз.")
            continue
        qty = int(ask_number("Кількість: ", integer=True))
        if qty <= 0:
            print("Кількість має бути додатною.")
            continue
        items.append((product, qty))
        print(f"  додано: {product.name} x {qty}")
    if not items:
        print("Замовлення скасовано: не додано жодного товару.")
        return
    order = shop.create_order(customer, items)
    print("\nЗамовлення оформлено.")
    print(order)


def show_customer_orders(shop: Shop) -> None:
    """Показує замовлення вибраного клієнта."""
    show_customers(shop)
    customer = pick_customer(shop)
    if not customer:
        return
    print(f"\n=== Замовлення: {customer.name} ===")
    if not customer.orders:
        print("Замовлень немає.")
        return
    for i, order in enumerate(customer.orders, start=1):
        print(f"\n№{i}\n{order}")


def save_shop(shop: Shop) -> None:
    """Зберігає товари, клієнтів і замовлення у файл."""
    shop.save_to_file(DATA_FILE)
    print(f"Стан збережено у файл: {DATA_FILE}")


MENU = """
======== Магазин ========
1. Показати товари
2. Показати клієнтів
3. Змінити ціну товару
4. Змінити кількість на складі
5. Додати товар
6. Додати клієнта
7. Оформити замовлення
8. Показати замовлення клієнта
9. Зберегти стан у файл
0. Вихід
"""

ACTIONS = {
    "1": show_products, "2": show_customers, "3": change_product_price,
    "4": change_product_stock, "5": add_new_product, "6": add_new_customer,
    "7": place_order, "8": show_customer_orders, "9": save_shop,
}


def run() -> None:
    """Запускає головне меню програми."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except (OSError, ValueError, AttributeError):
        pass
    try:
        shop = Shop.from_file(DATA_FILE)
    except (FileNotFoundError, ValueError) as error:
        print(f"Не вдалося завантажити магазин: {error}")
        return
    print(
        f"Завантажено товарів: {len(shop.products)}, "
        f"клієнтів: {len(shop.customers)}."
    )
    while True:
        print(MENU)
        choice = ask("Оберіть пункт: ")
        if choice == "0":
            print("До побачення.")
            break
        action = ACTIONS.get(choice)
        if not action:
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
