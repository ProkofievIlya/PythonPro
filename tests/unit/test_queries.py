from decimal import Decimal

import pytest

from catalog import queries
from tests.factories import BookFactory, CategoryFactory

pytestmark = pytest.mark.django_db


def test_books_in_stock():
    in_stock = BookFactory(stock=3)
    BookFactory(stock=0)
    assert list(queries.books_in_stock()) == [in_stock]


def test_books_by_price_range_is_inclusive():
    cheap = BookFactory(price=Decimal("50.00"))
    middle = BookFactory(price=Decimal("100.00"))
    BookFactory(price=Decimal("500.00"))
    result = queries.books_by_price_range(Decimal("50"), Decimal("100"))
    assert set(result) == {cheap, middle}


def test_search_books_matches_title_author_and_description():
    by_title = BookFactory(title="Zorro", author="A", description="x")
    by_author = BookFactory(title="B", author="Zorro Author", description="x")
    by_description = BookFactory(title="C", author="C", description="about zorro")
    BookFactory(title="Other", author="Other", description="nothing")
    assert set(queries.search_books("zorro")) == {by_title, by_author, by_description}


def test_available_or_cheap_books_has_no_duplicates():
    both = BookFactory(stock=5, price=Decimal("10.00"))
    only_cheap = BookFactory(stock=0, price=Decimal("10.00"))
    BookFactory(stock=0, price=Decimal("999.00"))
    result = queries.available_or_cheap_books(Decimal("20"))
    assert sorted(b.pk for b in result) == sorted([both.pk, only_cheap.pk])


def test_categories_with_stats_annotations():
    category = CategoryFactory()
    BookFactory(category=category, stock=2, price=Decimal("10.00"))
    BookFactory(category=category, stock=3, price=Decimal("20.00"))
    stats = queries.categories_with_stats().get(pk=category.pk)
    assert stats.book_count == 2
    assert stats.total_stock == 5
    assert stats.avg_price == Decimal("15.00")


def test_top_categories_by_books_orders_and_limits():
    big = CategoryFactory()
    small = CategoryFactory()
    CategoryFactory()  # без книг - не потрапляє у вибірку
    BookFactory.create_batch(3, category=big)
    BookFactory(category=small)
    assert list(queries.top_categories_by_books(limit=5)) == [big, small]
    assert list(queries.top_categories_by_books(limit=1)) == [big]


def test_books_in_category_slug():
    category = CategoryFactory(slug="sci")
    mine = BookFactory(category=category)
    BookFactory()
    assert list(queries.books_in_category_slug("sci")) == [mine]
