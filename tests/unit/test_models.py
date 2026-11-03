from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import translation
from django.db.models import ProtectedError
from django.utils import timezone

from catalog.models import Book, Category, Order, OrderItem
from tests.factories import (
    BookFactory,
    CategoryFactory,
    OrderFactory,
    OrderItemFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


class TestCategory:
    def test_str_returns_name(self):
        assert str(CategoryFactory(name="Science")) == "Science"

    def test_slug_is_generated_from_name_when_empty(self):
        category = Category.objects.create(name="Fiction Books", slug="")
        assert category.slug == "fiction-books"

    def test_slug_supports_cyrillic(self):
        category = Category.objects.create(name="Художня література", slug="")
        assert category.slug == "художня-література"

    def test_explicit_slug_is_kept(self):
        category = Category.objects.create(name="Fiction", slug="custom-slug")
        assert category.slug == "custom-slug"

    def test_slug_must_be_unique(self):
        CategoryFactory(slug="same")
        with pytest.raises(IntegrityError), transaction.atomic():
            CategoryFactory(slug="same")

    def test_default_ordering_is_by_name(self):
        CategoryFactory(name="Zeta")
        CategoryFactory(name="Alpha")
        assert [c.name for c in Category.objects.all()] == ["Alpha", "Zeta"]


class TestBook:
    def test_str_contains_title_and_author(self):
        book = BookFactory(title="Kobzar", author="Shevchenko")
        assert str(book) == "Kobzar — Shevchenko"

    @pytest.mark.parametrize("stock, expected", [(0, False), (1, True), (25, True)])
    def test_in_stock(self, stock, expected):
        assert BookFactory(stock=stock).in_stock is expected

    def test_default_ordering_is_by_title(self):
        BookFactory(title="B title")
        BookFactory(title="A title")
        assert [b.title for b in Book.objects.all()] == ["A title", "B title"]

    def test_created_at_is_set_automatically(self):
        assert BookFactory().created_at is not None

    def test_deleting_category_cascades_to_books(self):
        book = BookFactory()
        book.category.delete()
        assert not Book.objects.filter(pk=book.pk).exists()

    def test_related_name_books(self):
        category = CategoryFactory()
        BookFactory.create_batch(3, category=category)
        assert category.books.count() == 3

    def test_price_keeps_two_decimal_places(self):
        book = BookFactory(price=Decimal("199.5"))
        book.refresh_from_db()
        assert book.price == Decimal("199.50")


class TestLocalizedFields:
    def test_book_uses_english_fields_only_in_english(self):
        book = BookFactory(
            title="Кобзар", author="Тарас Шевченко", description="Опис",
            title_en="Kobzar", author_en="Taras Shevchenko", description_en="Description",
        )
        with translation.override("en"):
            assert (book.localized_title, book.localized_author, book.localized_description) == (
                "Kobzar", "Taras Shevchenko", "Description",
            )
        with translation.override("uk"):
            assert (book.localized_title, book.localized_author, book.localized_description) == (
                "Кобзар", "Тарас Шевченко", "Опис",
            )

    def test_book_falls_back_to_base_text_when_translation_is_empty(self):
        book = BookFactory(title="Кобзар", author="Автор", description="Опис")
        with translation.override("en"):
            assert book.localized_title == "Кобзар"
            assert book.localized_author == "Автор"
            assert book.localized_description == "Опис"

    def test_category_localized_name(self):
        category = CategoryFactory(name="Художня", name_en="Fiction")
        with translation.override("en"):
            assert category.localized_name == "Fiction"
        with translation.override("uk"):
            assert category.localized_name == "Художня"
        assert CategoryFactory(name="Наукова").localized_name == "Наукова"



class TestCoverUrl:
    def test_uploaded_cover_has_priority(self):
        book = BookFactory(pk=1, cover="covers/my.jpg")
        assert book.cover_url == "/media/covers/my.jpg"

    def test_demo_cover_from_static_by_id(self):
        assert BookFactory(pk=1).cover_url == "/static/img/books/1.jpg"

    def test_placeholder_when_no_cover(self):
        assert BookFactory(pk=99999).cover_url == "/static/img/books/placeholder.svg"


class TestOrder:
    def test_default_status_is_pending(self):
        assert OrderFactory().status == Order.Status.PENDING

    def test_str_contains_pk(self):
        order = OrderFactory()
        assert f"#{order.pk}" in str(order)

    def test_stripe_session_id_defaults_to_none(self):
        assert OrderFactory().stripe_session_id is None

    def test_stripe_session_id_must_be_unique(self):
        OrderFactory(stripe_session_id="cs_same")
        with pytest.raises(IntegrityError), transaction.atomic():
            OrderFactory(stripe_session_id="cs_same")

    def test_orders_are_sorted_newest_first(self):
        old_order = OrderFactory()
        new_order = OrderFactory()
        Order.objects.filter(pk=old_order.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        assert list(Order.objects.all()) == [new_order, old_order]

    def test_user_with_orders_cannot_be_deleted(self):
        order = OrderFactory()
        with pytest.raises(ProtectedError):
            order.user.delete()

    @pytest.mark.parametrize(
        "status", [Order.Status.PENDING, Order.Status.PAID, Order.Status.CANCELLED]
    )
    def test_status_choices_have_labels(self, status):
        assert str(status.label)


class TestOrderItem:
    def test_line_total_multiplies_price_by_quantity(self):
        item = OrderItemFactory(price=Decimal("10.50"), quantity=3)
        assert item.line_total == Decimal("31.50")

    def test_str_contains_book_and_quantity(self):
        item = OrderItemFactory(quantity=2)
        assert str(item) == f"{item.book} × 2"

    def test_book_with_order_items_is_protected(self):
        item = OrderItemFactory()
        with pytest.raises(ProtectedError):
            item.book.delete()

    def test_items_are_deleted_with_order(self):
        item = OrderItemFactory()
        item.order.delete()
        assert not OrderItem.objects.filter(pk=item.pk).exists()


class TestCustomUser:
    def test_str_returns_username(self):
        assert str(UserFactory(username="ilya")) == "ilya"

    def test_phone_is_optional(self):
        assert UserFactory().phone == ""
