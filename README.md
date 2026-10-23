# Bookstore

Навчальний каталог книг на Django: список і картка книги, додавання та редагування, вхід користувачів і права доступу.

## Можливості

- Категорії та книги, адмінка
- Сторінки каталогу на Bootstrap: список, деталі, форма, видалення
- Пошук, фільтр за категорією та наявністю, пагінація по 4 книги
- Свій користувач (`CustomUser`, поле `phone`)
- Реєстрація, вхід і вихід. Кнопка GitHub з’являється, якщо в `.env` задані ключі
- Групи «Менеджери каталогу» та «Переглядачі»
- Додавати, змінювати і видаляти книги можуть лише користувачі з відповідним правом
- Django Debug Toolbar (коли `DEBUG=True`)
- Лог запитів у консоль і файл `logs/django.log`
- Кошик у сесії, замовлення і оплата Stripe Checkout
- Лист на email після створення замовлення (у розробці друкується в консоль контейнера)

## Вимоги

- Python 3.10+
- pip

## Запуск у Docker

Потрібні Docker і Docker Compose. У `.env` уже мають бути змінні PostgreSQL і Redis (зразок у `.env.example`).

```powershell
docker compose up --build
```

Сайт: http://127.0.0.1:8001/

Контейнер `web` сам виконує `migrate` і `collectstatic`. Дані PostgreSQL лежать у volume `postgres_data`, зібрана статика — у `static_data`.

## Запуск без Docker

PostgreSQL і Redis мають уже працювати. У `.env` поставте `POSTGRES_HOST=localhost` і `REDIS_URL=redis://127.0.0.1:6379/1`.

```powershell
cd "шлях\до\Django_Lesson"
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

У `.env` задайте `DJANGO_SECRET_KEY`. Якщо в ключі є `#` або `$`, візьміть значення в лапки.

- Сайт: http://127.0.0.1:8000/
- Вхід: http://127.0.0.1:8000/accounts/login/
- Реєстрація: http://127.0.0.1:8000/accounts/signup/
- Адмінка: http://127.0.0.1:8000/admin/

Суперкористувач бачить усі дії з книгами. Звичайного користувача після реєстрації треба додати в групу в адмінці, інакше він може лише переглядати каталог.

## Структура

```
bookstore/          налаштування, логування, middleware
accounts/           користувач, групи
catalog/            моделі, сторінки каталогу, форми
templates/          вхід, реєстрація, сторінки 403, 404, 500
static/             свої стилі
```

## Змінні оточення

| Змінна | Опис |
|--------|------|
| `DJANGO_SECRET_KEY` | Секретний ключ |
| `DJANGO_DEBUG` | `True` або `False` |
| `DJANGO_ALLOWED_HOSTS` | Хости через кому |
| `GITHUB_CLIENT_ID` | Необов’язково, для кнопки GitHub |
| `GITHUB_CLIENT_SECRET` | Необов’язково, для кнопки GitHub |

Пароль у `.env` не зберігається. Файл `.env` у git не потрапляє.

Для GitHub OAuth callback: `http://127.0.0.1:8000/accounts/github/login/callback/`

## Демо-дані

```powershell
python manage.py seed_demo
```

Команда додає 3 категорії та кілька книг, якщо їх ще немає.
