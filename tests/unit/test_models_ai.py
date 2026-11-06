"""Тести моделей Category, Book, Order, OrderItem, створені за допомогою AI.

Кожен тест перевірено вручну й за потреби змінено (див. AI_REVIEW.md та AI_PROMPTS.md).
"""

from decimal import Decimal

import pytest
from django.utils import translation

from catalog.models import Book, Category, Order, OrderItem
from tests.factories import BookFactory, CategoryFactory, OrderFactory, OrderItemFactory

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


class TestCategoryAI:
    def test_slug_is_built_from_name_with_spaces(self):
        # Generated with AI, reviewed and modified
        category = Category.objects.create(name="Science Fiction")
        assert category.slug == "science-fiction"

    def test_localized_name_falls_back_to_base_in_english(self):
        # Generated with AI, reviewed and modified
        category = CategoryFactory(name="Фантастика", name_en="")
        with translation.override("en"):
            assert category.localized_name == "Фантастика"

    def test_localized_name_uses_english_when_filled(self):
        # Generated with AI, reviewed and modified
        category = CategoryFactory(name="Фантастика", name_en="Fiction")
        with translation.override("en"):
            assert category.localized_name == "Fiction"
        with translation.override("uk"):
            assert category.localized_name == "Фантастика"


class TestBookAI:
    def test_str_has_title_dash_author(self):
        # Generated with AI, reviewed and modified
        book = BookFactory(title="Kobzar", author="Shevchenko")
        assert str(book) == "Kobzar — Shevchenko"

    def test_localized_author_and_description_in_english(self):
        # Generated with AI, reviewed and modified
        book = BookFactory(
            author="Тарас Шевченко",
            author_en="Taras Shevchenko",
            description="Опис",
            description_en="Description",
        )
        with translation.override("en"):
            assert book.localized_author == "Taras Shevchenko"
            assert book.localized_description == "Description"
        with translation.override("uk"):
            assert book.localized_author == "Тарас Шевченко"
            assert book.localized_description == "Опис"

    @pytest.mark.parametrize("field", ["title", "author", "description"])
    def test_localized_field_falls_back_when_english_is_empty(self, field):
        # Generated with AI, reviewed and modified
        book = BookFactory(**{field: "Базовий текст", f"{field}_en": ""})
        with translation.override("en"):
            assert getattr(book, f"localized_{field}") == "Базовий текст"

    @pytest.mark.parametrize("stock, expected", [(0, False), (1, True), (50, True)])
    def test_in_stock_boundaries(self, stock, expected):
        # Generated with AI, reviewed and modified
        assert BookFactory(stock=stock).in_stock is expected

    def test_unsaved_book_uses_placeholder_cover(self):
        # Generated with AI, reviewed and modified
        book = Book(title="Draft", author="Nobody")
        assert book.cover_url == "/static/img/books/placeholder.svg"

    def test_book_is_linked_to_its_category(self):
        # Generated with AI, reviewed and modified
        category = CategoryFactory()
        book = BookFactory(category=category)
        assert list(category.books.all()) == [book]


class TestOrderAI:
    def test_status_values_and_labels(self):
        # Generated with AI, reviewed and modified
        assert Order.Status.PENDING.value == "pending"
        assert Order.Status.PAID.value == "paid"
        assert Order.Status.CANCELLED.value == "cancelled"
        assert len({str(label) for label in Order.Status.labels}) == 3

    def test_new_order_defaults(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory()
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING
        assert order.total == Decimal("0.00")
        assert order.stripe_session_id is None

    def test_several_orders_without_stripe_session_are_allowed(self):
        # Generated with AI, reviewed and modified
        OrderFactory()
        OrderFactory()
        assert Order.objects.filter(stripe_session_id__isnull=True).count() == 2

    def test_order_items_sum_matches_line_totals(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory()
        OrderItemFactory(order=order, price=Decimal("10.50"), quantity=2)
        OrderItemFactory(order=order, price=Decimal("4.00"), quantity=3)
        total = sum(item.line_total for item in order.items.all())
        assert total == Decimal("33.00")

    def test_email_is_taken_from_user_by_factory(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory()
        assert order.email == order.user.email


class TestOrderItemAI:
    def test_line_total_keeps_cents(self):
        # Generated with AI, reviewed and modified
        item = OrderItemFactory(price=Decimal("19.99"), quantity=3)
        assert item.line_total == Decimal("59.97")

    def test_default_quantity_is_one(self):
        # Generated with AI, reviewed and modified
        order = OrderFactory()
        book = BookFactory()
        item = OrderItem.objects.create(order=order, book=book, price=Decimal("10"))
        assert item.quantity == 1

    def test_item_price_is_a_snapshot_of_book_price(self):
        # Generated with AI, reviewed and modified
        book = BookFactory(price=Decimal("100.00"))
        item = OrderItemFactory(book=book)
        book.price = Decimal("150.00")
        book.save()
        item.refresh_from_db()
        assert item.price == Decimal("100.00")
