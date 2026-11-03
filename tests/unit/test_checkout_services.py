"""Сервіси оформлення замовлення: Stripe і email замінені mock-ами."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
import stripe
from django.utils import timezone

from catalog import checkout
from catalog.cart import Cart
from catalog.models import Book, Order
from tests.factories import BookFactory, OrderFactory, OrderItemFactory, UserFactory

pytestmark = pytest.mark.django_db


class FakeSession(dict):
    modified = False


class FakeRequest:
    def __init__(self):
        self.session = FakeSession()

    def build_absolute_uri(self, path):
        return f"http://testserver{path}"


def make_cart(*pairs):
    cart = Cart(FakeRequest())
    for book, quantity in pairs:
        cart.add(book, quantity)
    return cart


class TestCreateOrder:
    def test_creates_order_items_and_reduces_stock(self, django_capture_on_commit_callbacks):
        user = UserFactory()
        book = BookFactory(price=Decimal("40.00"), stock=5)
        with mock.patch.object(checkout, "send_order_email") as send_email:
            with django_capture_on_commit_callbacks(execute=True):
                order = checkout.create_order(user, "a@example.com", make_cart((book, 2)))
        book.refresh_from_db()
        assert order.total == Decimal("80.00")
        assert order.status == Order.Status.PENDING
        assert order.items.count() == 1
        assert book.stock == 3
        send_email.assert_not_called()  # лист - лише після оплати

    def test_caps_quantity_by_current_stock(self):
        user = UserFactory()
        book = BookFactory(stock=3)
        cart = make_cart((book, 3))
        Book.objects.filter(pk=book.pk).update(stock=1)  # хтось встиг купити
        order = checkout.create_order(user, "a@example.com", cart)
        assert order.items.get().quantity == 1
        book.refresh_from_db()
        assert book.stock == 0

    def test_empty_cart_raises_and_creates_nothing(self):
        user = UserFactory()
        with pytest.raises(ValueError):
            checkout.create_order(user, "a@example.com", make_cart())
        assert Order.objects.count() == 0


class TestStartCheckout:
    def test_builds_stripe_session_with_line_items(self):
        order = OrderFactory(email="buyer@example.com")
        item = OrderItemFactory(order=order, price=Decimal("12.34"), quantity=2)
        fake_session = mock.Mock(id="cs_test_1", url="https://stripe.test/pay")
        with mock.patch("stripe.checkout.Session.create", return_value=fake_session) as create:
            url = checkout.start_checkout(FakeRequest(), order)
        assert url == "https://stripe.test/pay"
        kwargs = create.call_args.kwargs
        assert kwargs["mode"] == "payment"
        assert kwargs["customer_email"] == "buyer@example.com"
        assert kwargs["client_reference_id"] == str(order.pk)
        line = kwargs["line_items"][0]
        assert line["quantity"] == 2
        assert line["price_data"]["unit_amount"] == 1234
        assert line["price_data"]["currency"] == "uah"
        assert line["price_data"]["product_data"]["name"] == item.book.title
        assert kwargs["success_url"].startswith("http://testserver/checkout/success/")
        order.refresh_from_db()
        assert order.stripe_session_id == "cs_test_1"


class TestMarkOrderPaid:
    def test_marks_pending_order_as_paid(self):
        order = OrderFactory(stripe_session_id="cs_1")
        assert checkout.mark_order_paid("cs_1").status == Order.Status.PAID
        order.refresh_from_db()
        assert order.status == Order.Status.PAID

    def test_sends_email_after_payment(self, django_capture_on_commit_callbacks):
        order = OrderFactory(stripe_session_id="cs_1")
        with mock.patch.object(checkout, "send_order_email") as send_email:
            with django_capture_on_commit_callbacks(execute=True):
                checkout.mark_order_paid("cs_1")
        send_email.assert_called_once_with(order.pk)

    def test_is_idempotent_and_does_not_resend_email(self, django_capture_on_commit_callbacks):
        OrderFactory(stripe_session_id="cs_1", status=Order.Status.PAID)
        with mock.patch.object(checkout, "send_order_email") as send_email:
            with django_capture_on_commit_callbacks(execute=True):
                assert checkout.mark_order_paid("cs_1").status == Order.Status.PAID
        send_email.assert_not_called()

    def test_cancelled_order_is_not_marked_paid(self):
        OrderFactory(stripe_session_id="cs_1", status=Order.Status.CANCELLED)
        assert checkout.mark_order_paid("cs_1").status == Order.Status.CANCELLED

    def test_unknown_session_returns_none(self):
        assert checkout.mark_order_paid("cs_missing") is None


class TestIsSessionPaid:
    def test_paid(self, stripe_paid_session):
        assert checkout.is_session_paid("cs_1") is True
        stripe_paid_session.assert_called_once_with("cs_1")

    def test_unpaid(self, stripe_unpaid_session):
        assert checkout.is_session_paid("cs_1") is False

    def test_stripe_error_means_not_paid(self):
        error = stripe.InvalidRequestError("No such session", "id")
        with mock.patch("stripe.checkout.Session.retrieve", side_effect=error):
            assert checkout.is_session_paid("cs_bad") is False

    def test_without_key_stripe_is_not_called(self, settings):
        settings.STRIPE_SECRET_KEY = ""
        with mock.patch("stripe.checkout.Session.retrieve") as retrieve:
            assert checkout.is_session_paid("cs_1") is False
        retrieve.assert_not_called()

    def test_empty_session_id(self):
        assert checkout.is_session_paid("") is False


class TestCancelHelpers:
    def test_cancel_order_by_session(self):
        book = BookFactory(stock=0)
        order = OrderFactory(stripe_session_id="cs_exp")
        OrderItemFactory(order=order, book=book, quantity=2)
        assert checkout.cancel_order_by_session("cs_exp").status == Order.Status.CANCELLED
        book.refresh_from_db()
        assert book.stock == 2

    def test_cancel_order_by_unknown_session(self):
        assert checkout.cancel_order_by_session("cs_none") is None

    def test_cancel_stale_orders_only_touches_old_pending(self):
        old = OrderFactory()
        fresh = OrderFactory()
        old_paid = OrderFactory(status=Order.Status.PAID)
        long_ago = timezone.now() - timedelta(hours=30)
        Order.objects.filter(pk__in=[old.pk, old_paid.pk]).update(created_at=long_ago)
        assert checkout.cancel_stale_orders(timedelta(hours=24)) == 1
        statuses = dict(Order.objects.values_list("pk", "status"))
        assert statuses == {
            old.pk: Order.Status.CANCELLED,
            fresh.pk: Order.Status.PENDING,
            old_paid.pk: Order.Status.PAID,
        }


class TestCancelOrder:
    def test_restores_stock_and_cancels(self):
        book = BookFactory(stock=1)
        order = OrderFactory()
        OrderItemFactory(order=order, book=book, quantity=4)
        checkout.cancel_order(order)
        book.refresh_from_db()
        order.refresh_from_db()
        assert book.stock == 5
        assert order.status == Order.Status.CANCELLED

    def test_paid_order_is_not_cancelled(self):
        book = BookFactory(stock=1)
        order = OrderFactory(status=Order.Status.PAID)
        OrderItemFactory(order=order, book=book, quantity=4)
        checkout.cancel_order(order)
        book.refresh_from_db()
        order.refresh_from_db()
        assert book.stock == 1
        assert order.status == Order.Status.PAID


class TestSendOrderEmail:
    def test_sends_email_with_order_lines(self, mailoutbox):
        order = OrderFactory(email="buyer@example.com", total=Decimal("30.00"))
        OrderItemFactory(order=order, price=Decimal("15.00"), quantity=2)
        checkout.send_order_email(order.pk)
        assert len(mailoutbox) == 1
        message = mailoutbox[0]
        assert message.to == ["buyer@example.com"]
        assert str(order.pk) in message.subject
        assert "× 2" in message.body

    def test_skips_order_without_email(self, mailoutbox):
        order = OrderFactory(email="")
        checkout.send_order_email(order.pk)
        assert mailoutbox == []

    def test_uses_send_mail_with_configured_sender(self, settings):
        settings.DEFAULT_FROM_EMAIL = "shop@example.com"
        order = OrderFactory(email="buyer@example.com")
        with mock.patch.object(checkout, "send_mail") as send_mail:
            checkout.send_order_email(order.pk)
        kwargs = send_mail.call_args.kwargs
        assert kwargs["from_email"] == "shop@example.com"
        assert kwargs["recipient_list"] == ["buyer@example.com"]
        assert kwargs["fail_silently"] is False
