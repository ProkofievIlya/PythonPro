"""Async-в'ю: перевіряємо і звичайним клієнтом, і AsyncClient (через async_to_sync).

async_to_sync виконує sync-ORM у потоці тесту, тому транзакція pytest-django
залишається видимою - transaction=True не потрібен.
"""

from decimal import Decimal

import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient
from django.urls import reverse

from catalog.async_views import SEARCH_LIMIT
from catalog.models import Category, Order
from tests.factories import (
    BookFactory,
    CategoryFactory,
    OrderFactory,
    OrderItemFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


class TestStatsApi:
    def test_empty_catalog(self, client):
        response = client.get(reverse("catalog:api_stats"))
        assert response.status_code == 200
        assert response.json() == {
            "books_total": 0,
            "books_in_stock": 0,
            "categories_total": 0,
            "total_stock": 0,
            "avg_price": 0,
        }

    def test_counts_and_aggregates(self, client):
        BookFactory(price=Decimal("100.00"), stock=2)
        BookFactory(price=Decimal("200.00"), stock=0)
        data = client.get(reverse("catalog:api_stats")).json()
        assert data["books_total"] == 2
        assert data["books_in_stock"] == 1
        assert data["categories_total"] == 2
        assert data["total_stock"] == 2
        assert data["avg_price"] == 150.0

    def test_only_get_is_allowed(self, client):
        assert client.post(reverse("catalog:api_stats")).status_code == 405

    def test_works_with_async_client(self):
        BookFactory(stock=4)
        response = async_to_sync(AsyncClient().get)(reverse("catalog:api_stats"))
        assert response.status_code == 200
        assert response.json()["books_total"] == 1
        assert response["Content-Type"].startswith("application/json")


class TestSearchApi:
    def test_returns_matching_books(self, client):
        BookFactory(title="Alpha", author="Someone", price=Decimal("10.00"), stock=3)
        BookFactory(title="Beta", author="Other")
        data = client.get(reverse("catalog:api_books"), {"q": "alpha"}).json()
        assert data["count"] == 1
        item = data["results"][0]
        assert item["title"] == "Alpha"
        assert item["price"] == "10.00"
        assert item["in_stock"] is True
        assert item["category"]

    def test_applies_category_and_stock_filters(self, client):
        category = CategoryFactory()
        wanted = BookFactory(category=category, stock=1)
        BookFactory(category=category, stock=0)
        BookFactory(stock=5)
        data = client.get(
            reverse("catalog:api_books"), {"category": category.pk, "in_stock": "1"}
        ).json()
        assert [r["id"] for r in data["results"]] == [wanted.pk]

    def test_results_are_limited_but_count_is_total(self, client):
        BookFactory.create_batch(SEARCH_LIMIT + 5)
        data = client.get(reverse("catalog:api_books")).json()
        assert data["count"] == SEARCH_LIMIT + 5
        assert len(data["results"]) == SEARCH_LIMIT

    def test_cyrillic_is_not_escaped(self, client):
        BookFactory(title="Кобзар")
        response = client.get(reverse("catalog:api_books"))
        assert "Кобзар" in response.content.decode("utf-8")

    def test_works_with_async_client(self):
        BookFactory(title="Async book")
        response = async_to_sync(AsyncClient().get)(
            reverse("catalog:api_books"), {"q": "async"}
        )
        assert response.json()["count"] == 1


    def test_returns_english_texts_for_english_language(self, client):
        BookFactory(
            title="Кобзар", title_en="Kobzar", author="Автор", author_en="Author",
            category__name="Художня", category__name_en="Fiction",
        )
        data = client.get(reverse("catalog:api_books"), HTTP_ACCEPT_LANGUAGE="en").json()
        item = data["results"][0]
        assert (item["title"], item["author"], item["category"]) == ("Kobzar", "Author", "Fiction")
        ukrainian = client.get(reverse("catalog:api_books")).json()["results"][0]
        assert ukrainian["title"] == "Кобзар"

    def test_search_finds_english_title(self, client):
        BookFactory(title="Кобзар", title_en="Kobzar")
        data = client.get(reverse("catalog:api_books"), {"q": "kobzar"}).json()
        assert data["count"] == 1


class TestCategoryApi:
    def test_returns_category_with_sorted_books(self, client):
        category = CategoryFactory(name="Fiction", slug="fiction")
        BookFactory(category=category, title="B book")
        BookFactory(category=category, title="A book")
        BookFactory()  # з іншої категорії
        response = client.get(reverse("catalog:api_category", args=["fiction"]))
        data = response.json()
        assert response.status_code == 200
        assert data["name"] == "Fiction"
        assert [b["title"] for b in data["books"]] == ["A book", "B book"]

    def test_unknown_slug_returns_json_404(self, client):
        response = client.get(reverse("catalog:api_category", args=["missing"]))
        assert response.status_code == 404
        assert response.json() == {"error": "Категорію не знайдено."}

    def test_unicode_slug(self, client):
        category = Category.objects.create(name="Художня", slug="")
        response = client.get(reverse("catalog:api_category", args=[category.slug]))
        assert response.status_code == 200
        assert response.json()["slug"] == "художня"


class TestMyOrdersApi:
    def test_anonymous_gets_401(self, client):
        response = client.get(reverse("catalog:api_orders"))
        assert response.status_code == 401
        assert response.json() == {"error": "Потрібна авторизація."}

    def test_returns_only_own_orders(self, auth_client, user):
        mine = OrderFactory(user=user, total=Decimal("30.00"), status=Order.Status.PAID)
        OrderItemFactory.create_batch(2, order=mine)
        OrderFactory(user=UserFactory())  # чуже замовлення
        data = auth_client.get(reverse("catalog:api_orders")).json()
        assert data["count"] == 1
        row = data["results"][0]
        assert row["id"] == mine.pk
        assert row["status"] == "paid"
        assert row["status_display"] == "Оплачено"
        assert row["items_count"] == 2
        assert row["total"] == "30.00"

    def test_works_with_async_client_and_login(self, user):
        OrderFactory(user=user)
        client = AsyncClient()
        async_to_sync(client.aforce_login)(user)
        response = async_to_sync(client.get)(reverse("catalog:api_orders"))
        assert response.status_code == 200
        assert response.json()["count"] == 1
