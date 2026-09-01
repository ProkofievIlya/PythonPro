"""Навчальний Flask-додаток «Кінотека».

Міні-колекція фільмів з головною сторінкою, списком записів
і формою додавання нового фільму. Дані зберігаються у ``films.json``,
тому список не зникає після перезапуску сервера.

Маршрути
--------
``/``            головна сторінка
``/films``       список фільмів
``/films/add``   форма додавання (GET — показати, POST — зберегти)
``/about``       сторінка про проєкт
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from flask import Flask, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

app = Flask(__name__)
app.secret_key = "dev-secret-key"

DATA_FILE: Path = Path(__file__).resolve().parent / "films.json"


class Film(TypedDict):
    """Один запис кінотеки.

    Attributes:
        title: Назва фільму.
        year: Рік виходу.
        genre: Жанр або поєднання жанрів.
        rating: Особиста оцінка від 1 до 10.
    """

    title: str
    year: int
    genre: str
    rating: int


class FilmFormData(TypedDict):
    """Сирі дані форми додавання фільму (усі поля — рядки)."""

    title: str
    year: str
    genre: str
    rating: str


def default_films() -> list[Film]:
    """Повертає стартову колекцію, якщо файл даних ще не існує."""
    return [
        {
            "title": "Інтерстеллар",
            "year": 2014,
            "genre": "Наукова фантастика",
            "rating": 9,
        },
        {
            "title": "Паразити",
            "year": 2019,
            "genre": "Драма / трилер",
            "rating": 9,
        },
        {
            "title": "Дюна",
            "year": 2021,
            "genre": "Епічна фантастика",
            "rating": 8,
        },
    ]


def load_films() -> list[Film]:
    """Читає колекцію з ``films.json`` або створює файл зі стартовими даними.

    Returns:
        Список фільмів. Якщо файл пошкоджений — повертає стартову колекцію.
    """
    if not DATA_FILE.exists():
        items = default_films()
        save_films(items)
        return items

    try:
        raw: object = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_films()

    if not isinstance(raw, list):
        return default_films()

    items: list[Film] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            items.append(
                {
                    "title": str(row.get("title", "")).strip(),
                    "year": int(row["year"]),
                    "genre": str(row.get("genre", "")).strip(),
                    "rating": int(row["rating"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return items or default_films()


def save_films(items: list[Film]) -> None:
    """Записує колекцію фільмів у ``films.json``.

    Args:
        items: Поточний список фільмів.
    """
    DATA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def validate_film_form(
    title: str,
    year: str,
    genre: str,
    rating: str,
) -> list[str]:
    """Перевіряє дані форми додавання фільму.

    Args:
        title: Назва фільму.
        year: Рік виходу у вигляді рядка з форми.
        genre: Жанр.
        rating: Оцінка у вигляді рядка з форми.

    Returns:
        Список повідомлень про помилки. Порожній список означає,
        що всі поля заповнені коректно.
    """
    errors: list[str] = []

    if not title:
        errors.append("Вкажіть назву фільму.")
    if not year.isdigit() or not (1888 <= int(year) <= 2100):
        errors.append("Рік має бути числом від 1888 до 2100.")
    if not genre:
        errors.append("Вкажіть жанр.")
    if not rating.isdigit() or not (1 <= int(rating) <= 10):
        errors.append("Оцінка має бути від 1 до 10.")

    return errors


films: list[Film] = load_films()


@app.context_processor
def inject_template_globals() -> dict[str, object]:
    """Додає в усі шаблони назву активного маршруту для підсвітки меню."""
    return {"active_page": request.endpoint or ""}


@app.route("/")
def index() -> ResponseReturnValue:
    """Головна (лендінг) сторінка кінотеки.

    Returns:
        HTML-сторінка з короткою презентацією проєкту
        та кількістю фільмів у списку.
    """
    return render_template("index.html", films_count=len(films))


@app.route("/films")
def films_list() -> ResponseReturnValue:
    """Сторінка зі списком усіх фільмів.

    Returns:
        HTML-сторінка з поточною колекцією.
    """
    return render_template("items.html", films=films)


@app.route("/films/add", methods=["GET", "POST"])
def add_film() -> ResponseReturnValue:
    """Показує форму додавання або зберігає новий фільм.

    GET:
        Відображає окремий шаблон форми.
    POST:
        Валідує поля форми. Якщо є помилки — показує їх і форму знову.
        Якщо дані коректні — додає фільм, зберігає файл і перенаправляє на ``/films``.

    Returns:
        HTML-сторінка з формою або редірект на список фільмів.
    """
    if request.method == "POST":
        title: str = request.form.get("title", "").strip()
        year: str = request.form.get("year", "").strip()
        genre: str = request.form.get("genre", "").strip()
        rating: str = request.form.get("rating", "").strip()

        errors: list[str] = validate_film_form(title, year, genre, rating)
        form: FilmFormData = {
            "title": title,
            "year": year,
            "genre": genre,
            "rating": rating,
        }
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("add.html", form=form)

        new_film: Film = {
            "title": title,
            "year": int(year),
            "genre": genre,
            "rating": int(rating),
        }
        films.append(new_film)
        save_films(films)
        flash(f"Фільм «{title}» додано до кінотеки.", "success")
        return redirect(url_for("films_list"))

    return render_template("add.html", form=None)


@app.route("/about")
def about() -> ResponseReturnValue:
    """Сторінка з описом навчального проєкту.

    Returns:
        HTML-сторінка «Про проєкт».
    """
    return render_template("about.html", films_count=len(films))


@app.errorhandler(404)
def page_not_found(_error: object) -> tuple[str, int]:
    """Показує сторінку, якщо користувач відкрив неіснуючу адресу.

    Args:
        _error: Об'єкт помилки Flask (не використовується).

    Returns:
        Кортеж із HTML-сторінки 404 і коду відповіді.
    """
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
