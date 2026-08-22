"""Урок 3. Базові типи даних, анотації типів та документація.

У цьому файлі функції мають:
- анотації типів (type hints) — підказки про типи параметрів і результату;
- документацію (docstring) — текст у потрійних лапках одразу після заголовка функції.
"""

from typing import Any, Callable


# 1. Рядки
def string_length(text: str) -> int:
    """Повертає кількість символів у рядку text."""
    return len(text)


def concat_strings(text1: str, text2: str) -> str:
    """З'єднує два рядки text1 і text2 та повертає результат."""
    return text1 + text2


# 2. Числа
def square(number: int | float) -> int | float:
    """Повертає квадрат числа number (цілого або дробового)."""
    return number * number


def add_numbers(a: int | float, b: int | float) -> int | float:
    """Повертає суму двох чисел a і b."""
    return a + b


def divide_int(a: int, b: int) -> tuple[int, int]:
    """Ділить a на b націло.

    Повертає:
        Кортеж (ціла частина, остача від ділення).
    """
    return a // b, a % b


# 3. Списки
def average(numbers: list[int | float]) -> float:
    """Повертає середнє арифметичне елементів списку numbers."""
    total = 0
    count = len(numbers)
    for i in range(count):
        total = total + numbers[i]
    return total / count


def common_elements(list1: list[Any], list2: list[Any]) -> list[Any]:
    """Повертає спільні елементи двох списків без повторень."""
    return list(set(list1) & set(list2))


# 4. Словники
def print_keys(dictionary: dict[str, Any]) -> None:
    """Виводить усі ключі словника dictionary."""
    for key in dictionary:
        print(key)


def merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Об'єднує два словники. Якщо ключ повторюється, береться значення з dict2."""
    new_dict = {}
    for key in dict1:
        new_dict[key] = dict1[key]
    for key in dict2:
        new_dict[key] = dict2[key]
    return new_dict


# 5. Множини
def union_sets(set1: set[Any], set2: set[Any]) -> set[Any]:
    """Повертає об'єднання двох множин (усі унікальні елементи з обох)."""
    return set1.union(set2)


def is_subset(set1: set[Any], set2: set[Any]) -> bool:
    """Перевіряє, чи є set1 підмножиною set2. Повертає True або False."""
    return set1.issubset(set2)


# 6. Умовні вирази та цикли
def even_or_odd(number: int) -> None:
    """Виводить 'Парне' або 'Непарне' залежно від числа number."""
    if number % 2 == 0:
        print("Парне")
    else:
        print("Непарне")


def even_numbers(numbers: list[int]) -> list[int]:
    """Повертає новий список лише з парних чисел зі списку numbers."""
    result = []
    for i in range(len(numbers)):
        if numbers[i] % 2 == 0:
            result.append(numbers[i])
    return result


# 7. Лямбда
# Приймає число і повертає "парне" або "не парне".
# У lambda немає docstring, тому опис записано коментарем.
check_even: Callable[[int], str] = lambda n: "парне" if n % 2 == 0 else "не парне"


print("----- 1. Рядки -----")
print(string_length("Привіт"))
print(concat_strings("Hello, ", "world!"))

print("----- 2. Числа -----")
print(square(5))
print(square(2.5))
print(add_numbers(3, 7))
print(add_numbers(1.5, 2.5))
print("ціла частина і залишок:", divide_int(17, 5))

print("----- 3. Списки -----")
print(average([10, 20, 30, 40]))
print(common_elements([1, 2, 3, 4, 2], [2, 4, 6, 8]))

print("----- 4. Словники -----")
d1 = {"ім'я": "Іван", "вік": 20, "група": "КН-21"}
print("ключі:")
print_keys(d1)
print(merge_dicts(d1, {"вік": 21, "місто": "Київ"}))

print("----- 5. Множини -----")
print(union_sets({1, 2, 3}, {3, 4, 5}))
print(is_subset({1, 2}, {1, 2, 3, 4}))
print(is_subset({1, 5}, {1, 2, 3}))

print("----- 6. Умови і цикли -----")
even_or_odd(8)
even_or_odd(7)
print(even_numbers([1, 2, 3, 4, 5, 6, 7, 8]))

print("----- 7. Лямбда -----")
print(check_even(10))
print(check_even(3))
