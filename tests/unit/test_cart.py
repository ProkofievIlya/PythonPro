from decimal import Decimal

import pytest

from catalog.cart import SESSION_KEY, Cart
from catalog.context_processors import cart_count


class FakeSession(dict):
    modified = False


class FakeRequest:
    def __init__(self, session=None):
        self.session = session if session is not None else FakeSession()


@pytest.fixture
def cart():
    return Cart(FakeRequest())


@pytest.mark.django_db
class TestCart:
    def test_new_cart_is_empty(self, cart):
        assert len(cart) == 0
        assert cart.total == Decimal("0")

    def test_add_book(self, cart, make_book):
        book = make_book(stock=5)
        cart.add(book)
        assert len(cart) == 1
        assert cart.cart == {str(book.pk): 1}

    def test_add_accumulates_quantity(self, cart, make_book):
        book = make_book(stock=5)
        cart.add(book)
        cart.add(book, quantity=2)
        assert len(cart) == 3

    def test_add_is_capped_by_stock(self, cart, make_book):
        book = make_book(stock=2)
        for _ in range(5):
            cart.add(book)
        assert len(cart) == 2

    def test_add_ignores_out_of_stock_book(self, cart, make_book):
        cart.add(make_book(stock=0))
        assert len(cart) == 0

    def test_add_ignores_non_positive_quantity(self, cart, make_book):
        cart.add(make_book(stock=3), quantity=0)
        assert len(cart) == 0

    def test_decrease_reduces_quantity(self, cart, make_book):
        book = make_book(stock=5)
        cart.add(book, quantity=3)
        cart.decrease(book)
        assert len(cart) == 2

    def test_decrease_to_zero_removes_item(self, cart, make_book):
        book = make_book(stock=5)
        cart.add(book)
        cart.decrease(book)
        assert str(book.pk) not in cart.cart

    def test_decrease_unknown_book_is_noop(self, cart, make_book):
        cart.decrease(make_book())
        assert len(cart) == 0

    def test_remove(self, cart, make_book):
        book = make_book(stock=5)
        cart.add(book, quantity=2)
        cart.remove(book)
        assert len(cart) == 0

    def test_remove_unknown_book_is_noop(self, cart, make_book):
        cart.remove(make_book())
        assert len(cart) == 0

    def test_clear(self, cart, make_book):
        cart.add(make_book(stock=5), quantity=2)
        cart.clear()
        assert len(cart) == 0
        assert cart.session[SESSION_KEY] == {}

    def test_total_and_iteration(self, cart, make_book):
        cheap = make_book(price=Decimal("10.00"), stock=5)
        pricey = make_book(price=Decimal("25.50"), stock=5)
        cart.add(cheap, quantity=2)
        cart.add(pricey)
        rows = {row["book"].pk: row for row in cart}
        assert rows[cheap.pk]["total"] == Decimal("20.00")
        assert rows[pricey.pk]["quantity"] == 1
        assert cart.total == Decimal("45.50")

    def test_iteration_skips_deleted_books(self, cart, make_book):
        book = make_book(stock=5)
        cart.add(book)
        book.delete()
        assert list(cart) == []

    def test_cart_reads_existing_session_data(self, make_book):
        book = make_book(stock=5)
        session = FakeSession({SESSION_KEY: {str(book.pk): 3}})
        assert len(Cart(FakeRequest(session))) == 3


class TestCartCountContextProcessor:
    def test_counts_all_quantities(self):
        request = FakeRequest(FakeSession({"cart": {"1": 2, "2": 3}}))
        assert cart_count(request) == {"cart_count": 5}

    def test_empty_session(self):
        assert cart_count(FakeRequest()) == {"cart_count": 0}

    def test_ignores_invalid_values(self):
        request = FakeRequest(FakeSession({"cart": {"1": "x", "2": 4}}))
        assert cart_count(request) == {"cart_count": 4}

    def test_request_without_session(self):
        assert cart_count(object()) == {"cart_count": 0}
