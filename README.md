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

### Швидкий запуск без Docker (SQLite)

```powershell
$env:DJANGO_SETTINGS_MODULE = "bookstore.settings_local"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`bookstore/settings_local.py` використовує файл `db_local.sqlite3` і кеш у пам'яті, тож PostgreSQL і Redis не потрібні.

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

## Інтернаціоналізація (uk + en)

- Мови: українська (за замовчуванням) і англійська, перемикач `UK / EN` у навбарі (`/i18n/setlang/`, мова зберігається в cookie `django_language`; також враховується `Accept-Language`).
- Вихідні рядки (msgid) — українські; переклади лежать у `locale/<мова>/LC_MESSAGES/django.po`, скомпільовані файли `django.mo` вже в репозиторії.
- Дані книг і категорій мають англійські поля (`title_en`, `author_en`, `description_en`, `name_en`): у англійському інтерфейсі показуються вони, а якщо поле порожнє — українське значення. Заповнюються в адмінці (блок «Англійською») або формі книги; `seed_demo` додає переклади демо-книг.
- Перекладено: verbose_name моделей і статуси замовлення, форми та їхні помилки, шаблони (`{% trans %}`, `{% blocktrans %}` з множиною), повідомлення `messages`, лист із замовленням, JSON-помилки API.
- Оновити переклади після зміни текстів (потрібен GNU gettext):

```powershell
python manage.py makemessages -l uk -l en
python manage.py compilemessages
```

- Без gettext (наприклад, на Windows) `.mo` можна зібрати зі `.po` скриптом: `python scripts/compile_messages.py`.

## Async-в'ю (async ORM)

| URL | Опис |
|-----|------|
| `/api/stats/` | кількість книг/категорій, залишок, середня ціна (`acount`, `aaggregate`, `asyncio.gather`) |
| `/api/books/?q=&category=&in_stock=1` | пошук книг (`async for` по QuerySet) |
| `/api/categories/<slug>/` | категорія з книгами (`aget`) |
| `/api/orders/` | замовлення поточного користувача (`await request.auser()`) |

## Тести

```powershell
pip install -r requirements-dev.txt
pytest
```

- `pytest-django` + `factory-boy` (`tests/factories.py`), налаштування `bookstore/settings_test.py` (SQLite у пам'яті, locmem-кеш і пошта — Postgres та Redis не потрібні).
- `tests/unit/` — моделі, форми, в'ю, корзина, сервіси оформлення, async API, i18n; `tests/integration/` — наскрізні сценарії користувача.
- Stripe і email замінені mock-ами (`unittest.mock`, `mailoutbox`), реальні запити не виконуються.
- Покриття: `pytest` одразу показує звіт `--cov`; поріг 70% задано в `.coveragerc` (`fail_under`). Окремі групи: `pytest -m unit`, `pytest -m integration`.

## Оплата Stripe: як це працює

- Після створення замовлення книги резервуються (зменшується залишок), користувача переводить на Stripe Checkout.
- Сторінка `/checkout/success/` **перепитує Stripe** (`Session.retrieve`) і позначає замовлення оплаченим лише при `payment_status == "paid"` і тільки для власника замовлення. Лист із замовленням надсилається після оплати.
- Webhook `/stripe/webhook/` приймає події **лише з перевіреним підписом**: без `STRIPE_WEBHOOK_SECRET` він відповідає 400. Обробляються `checkout.session.completed` / `async_payment_succeeded` (оплачено) та `checkout.session.expired` / `async_payment_failed` (замовлення скасовується, книги повертаються на склад).
- Локально секрет webhook дає Stripe CLI: `stripe listen --forward-to 127.0.0.1:8000/stripe/webhook/` (виведений `whsec_...` вписати в `.env`).
- Неоплачені замовлення, яким більше доби, можна скасувати вручну: `python manage.py cancel_stale_orders --hours 24`.

