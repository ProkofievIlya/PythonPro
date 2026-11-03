"""Спільні фікстури: користувачі, клієнти, фальшивий Stripe."""

from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import Permission
from django.utils import translation

from tests.factories import (
    DEFAULT_PASSWORD,
    BookFactory,
    CategoryFactory,
    OrderFactory,
    OrderItemFactory,
    UserFactory,
)

FAKE_STRIPE_URL = "https://checkout.stripe.test/pay/cs_test_123"


def pytest_collection_modifyitems(items):
    """Позначає тести маркерами unit / integration за каталогом."""
    for item in items:
        path = str(item.path).replace("\\", "/")
        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/tests/unit/" in path:
            item.add_marker(pytest.mark.unit)


@pytest.fixture(autouse=True)
def _reset_language():
    """LocaleMiddleware залишає активну мову після запиту - скидаємо її між тестами."""
    translation.activate("uk")
    yield
    translation.activate("uk")


@pytest.fixture
def password():
    return DEFAULT_PASSWORD


@pytest.fixture
def user(db):
    return UserFactory(username="reader", email="reader@example.com")


@pytest.fixture
def manager(db):
    """Користувач із правами add/change/delete/view на книги."""
    manager = UserFactory(username="manager", email="manager@example.com")
    perms = Permission.objects.filter(
        content_type__app_label="catalog",
        codename__in=["add_book", "change_book", "delete_book", "view_book"],
    )
    manager.user_permissions.add(*perms)
    return manager


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def manager_client(client, manager):
    client.force_login(manager)
    return client


@pytest.fixture
def category(db):
    return CategoryFactory(name="Fiction", slug="fiction")


@pytest.fixture
def book(category):
    return BookFactory(title="Kobzar", author="Taras Shevchenko", category=category)


@pytest.fixture
def make_book(category):
    def _make(**kwargs):
        kwargs.setdefault("category", category)
        return BookFactory(**kwargs)

    return _make


@pytest.fixture
def make_order():
    def _make(**kwargs):
        return OrderFactory(**kwargs)

    return _make


@pytest.fixture
def make_order_item():
    def _make(**kwargs):
        return OrderItemFactory(**kwargs)

    return _make


def stripe_event(event_type, session_id, payment_status="paid"):
    """Подія Stripe у тому вигляді, який повертає Webhook.construct_event."""
    return {
        "type": event_type,
        "data": {"object": {"id": session_id, "payment_status": payment_status}},
    }


@pytest.fixture
def stripe_paid_session():
    """Мок stripe.checkout.Session.retrieve: Stripe підтверджує оплату."""
    paid = SimpleNamespace(payment_status="paid")
    with mock.patch("stripe.checkout.Session.retrieve", return_value=paid) as m:
        yield m


@pytest.fixture
def stripe_unpaid_session():
    """Мок stripe.checkout.Session.retrieve: сесію не оплачено."""
    unpaid = SimpleNamespace(payment_status="unpaid")
    with mock.patch("stripe.checkout.Session.retrieve", return_value=unpaid) as m:
        yield m


@pytest.fixture
def stripe_webhook_event():
    """Мок stripe.Webhook.construct_event: підпис вважаємо валідним і повертаємо подію."""
    with mock.patch("stripe.Webhook.construct_event") as m:
        yield m


@pytest.fixture
def stripe_session_create():
    """Мок stripe.checkout.Session.create: жодних мережевих запитів до Stripe."""
    fake_session = SimpleNamespace(id="cs_test_123", url=FAKE_STRIPE_URL)
    with mock.patch("stripe.checkout.Session.create", return_value=fake_session) as m:
        yield m
