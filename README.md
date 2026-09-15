# Bookstore — каталог книг (Django)

Навчальний проєкт інтернет-магазину книг. Поточне завдання: моделі каталогу, адмін-панель, приклади ORM і міграції. Подальші домашні роботи розширюють цей же проєкт.

## Можливості

- Моделі **Category** (назва, slug) та **Book** (назва, автор, ціна, опис, залишок, категорія)
- **Django Admin**: інлайни книг у категорії, фільтри, пошук, швидке редагування ціни та залишку
- Модуль **`catalog/queries.py`**: `filter`, `annotate`, `Q`-об'єкти
- Налаштування через **`.env`** (секретний ключ, DEBUG, ALLOWED_HOSTS)

## Вимоги

- Python 3.10+
- pip

## Швидкий старт

```powershell
cd "шлях\до\777"
pip install -r requirements.txt
```

Скопіюйте шаблон змінних оточення:

```powershell
copy .env.example .env
```

У `.env` задайте `DJANGO_SECRET_KEY` (якщо в ключі є `#` або `$`, обгорніть значення в лапки).

Застосуйте міграції та створіть адміністратора:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Сайт: http://127.0.0.1:8000/
- Адмінка: http://127.0.0.1:8000/admin/

## Структура проєкту

```
bookstore/          # налаштування проєкту (settings, urls)
catalog/            # додаток каталогу
  models.py         # Category, Book
  admin.py          # реєстрація в admin
  queries.py        # приклади ORM
  migrations/       # міграції БД
manage.py
requirements.txt
.env.example        # зразок для .env (комітиться)
.env                # локальні секрети (не комітиться)
```

## Моделі

| Модель    | Поля |
|-----------|------|
| Category  | `name`, `slug` |
| Book      | `title`, `author`, `price`, `description`, `stock`, `category` (FK), `created_at` |

## ORM (приклади)

У Django shell:

```python
python manage.py shell
```

```python
from decimal import Decimal
from catalog.queries import (
    books_in_stock,
    search_books,
    categories_with_stats,
    available_or_cheap_books,
)

books_in_stock()
search_books("толстой")
categories_with_stats()
available_or_cheap_books(Decimal("200.00"))
```

## Змінні оточення

| Змінна | Опис |
|--------|------|
| `DJANGO_SECRET_KEY` | Секретний ключ Django |
| `DJANGO_DEBUG` | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Хости через кому, напр. `127.0.0.1,localhost` |

Пароль суперкористувача зберігається в базі (хеш), не в `.env`.

## База даних

За замовчуванням — SQLite (`db.sqlite3`). Демо-дані (3 категорії + 3 книги):

```powershell
python manage.py seed_demo
```

## Ліцензія

Навчальний проєкт.
