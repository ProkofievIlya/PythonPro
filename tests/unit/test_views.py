import json
from unittest import mock

import pytest
import stripe
from django.contrib.messages import get_messages
from django.urls import reverse, reverse_lazy

from catalog.models import Book, Order
from catalog.views import BOOKS_PER_PAGE, server_error
from tests.conftest import FAKE_STRIPE_URL, stripe_event

pytestmark = pytest.mark.django_db


def template_names(response):
    return [t.name for t in response.templates]


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


class TestHome:
    def test_shows_only_books_in_stock(self, client, make_book):
        visible = make_book(title="Visible", stock=2)
        make_book(title="Hidden", stock=0)
        response = client.get(reverse("catalog:home"))
        assert response.status_code == 200
        assert list(response.context["featured"]) == [visible]
        assert "catalog/home.html" in template_names(response)

    def test_features_at_most_four_books(self, client, make_book):
        for _ in range(6):
            make_book(stock=1)
        response = client.get(reverse("catalog:home"))
        assert len(list(response.context["featured"])) == 4


class TestBookList:
    @pytest.mark.parametrize(
        "url_name, view_type",
        [("catalog:book_list", "CBV"), ("catalog:book_list_fbv", "FBV")],
    )
    def test_list_works_for_cbv_and_fbv(self, client, make_book, url_name, view_type):
        make_book(title="Only one")
        response = client.get(reverse(url_name))
        assert response.status_code == 200
        assert response.context["view_type"] == view_type
        assert [b.title for b in response.context["books"]] == ["Only one"]

    def test_pagination(self, client, make_book):
        for i in range(BOOKS_PER_PAGE + 2):
            make_book(title=f"Title {i:02d}")
        first = client.get(reverse("catalog:book_list"))
        second = client.get(reverse("catalog:book_list"), {"page": 2})
        assert len(first.context["books"]) == BOOKS_PER_PAGE
        assert first.context["is_paginated"] is True
        assert len(second.context["books"]) == 2

    def test_fbv_out_of_range_page_returns_last_page(self, client, make_book):
        for i in range(BOOKS_PER_PAGE + 1):
            make_book(title=f"Title {i:02d}")
        response = client.get(reverse("catalog:book_list_fbv"), {"page": 999})
        assert response.status_code == 200
        assert response.context["page_obj"].number == 2

    def test_search_by_title_or_author(self, client, make_book):
        make_book(title="Alpha", author="Someone")
        make_book(title="Beta", author="Alphabet Writer")
        make_book(title="Gamma", author="Other")
        response = client.get(reverse("catalog:book_list"), {"q": "alpha"})
        assert sorted(b.title for b in response.context["books"]) == ["Alpha", "Beta"]
        assert response.context["filter_q"] == "alpha"

    def test_filter_by_category(self, client, make_book, category):
        from tests.factories import CategoryFactory

        other = CategoryFactory()
        mine = make_book(title="Mine", category=category)
        make_book(title="Theirs", category=other)
        response = client.get(reverse("catalog:book_list"), {"category": category.pk})
        assert list(response.context["books"]) == [mine]

    def test_non_numeric_category_is_ignored(self, client, make_book):
        make_book()
        response = client.get(reverse("catalog:book_list"), {"category": "abc"})
        assert response.status_code == 200
        assert len(response.context["books"]) == 1

    def test_filter_in_stock_only(self, client, make_book):
        available = make_book(title="Available", stock=3)
        make_book(title="Sold out", stock=0)
        response = client.get(reverse("catalog:book_list"), {"in_stock": "1"})
        assert list(response.context["books"]) == [available]

    def test_empty_catalog_shows_hint(self, client):
        response = client.get(reverse("catalog:book_list"))
        assert response.status_code == 200
        assert "seed_demo" in response.content.decode()

    def test_pagination_keeps_filters_in_links(self, client, make_book):
        for i in range(BOOKS_PER_PAGE + 1):
            make_book(title=f"Match {i:02d}")
        response = client.get(reverse("catalog:book_list"), {"q": "match"})
        assert "?page=2&amp;q=match" in response.content.decode() or "?page=2&q=match" in response.content.decode()


class TestBookDetail:
    def test_cbv_detail(self, client, book):
        response = client.get(reverse("catalog:book_detail", args=[book.pk]))
        assert response.status_code == 200
        assert response.context["book"] == book
        assert response.context["view_type"] == "CBV"

    def test_fbv_detail(self, client, book):
        response = client.get(reverse("catalog:book_detail_fbv", args=[book.pk]))
        assert response.status_code == 200
        assert response.context["view_type"] == "FBV"

    @pytest.mark.parametrize("name", ["catalog:book_detail", "catalog:book_detail_fbv"])
    def test_unknown_book_renders_custom_404(self, client, name):
        response = client.get(reverse(name, args=[999999]))
        assert response.status_code == 404
        assert "404.html" in template_names(response)

    def test_out_of_stock_book_has_no_add_to_cart_form(self, client, make_book):
        sold_out = make_book(stock=0)
        response = client.get(reverse("catalog:book_detail", args=[sold_out.pk]))
        assert reverse("catalog:cart_add", args=[sold_out.pk]) not in response.content.decode()


class TestCartViews:
    def test_add_puts_book_into_session(self, client, book):
        response = client.post(reverse("catalog:cart_add", args=[book.pk]))
        assert response.status_code == 302
        assert response.url == reverse("catalog:cart_detail")
        assert client.session["cart"] == {str(book.pk): 1}

    def test_add_requires_post(self, client, book):
        assert client.get(reverse("catalog:cart_add", args=[book.pk])).status_code == 405

    def test_add_unknown_book_returns_404(self, client):
        assert client.post(reverse("catalog:cart_add", args=[999999])).status_code == 404

    def test_add_out_of_stock_book_is_ignored(self, client, make_book):
        sold_out = make_book(stock=0)
        client.post(reverse("catalog:cart_add", args=[sold_out.pk]))
        assert client.session["cart"] == {}

    def test_decrease_remove_and_clear(self, client, make_book):
        first = make_book(stock=5)
        second = make_book(stock=5)
        for _ in range(3):
            client.post(reverse("catalog:cart_add", args=[first.pk]))
        client.post(reverse("catalog:cart_add", args=[second.pk]))
        client.post(reverse("catalog:cart_decrease", args=[first.pk]))
        assert client.session["cart"][str(first.pk)] == 2
        client.post(reverse("catalog:cart_remove", args=[second.pk]))
        assert str(second.pk) not in client.session["cart"]
        client.post(reverse("catalog:cart_clear"))
        assert client.session["cart"] == {}

    def test_cart_detail_lists_books_and_total(self, client, book):
        client.post(reverse("catalog:cart_add", args=[book.pk]))
        response = client.get(reverse("catalog:cart_detail"))
        assert response.status_code == 200
        assert book.title in response.content.decode()
        assert response.context["cart"].total == book.price

    def test_empty_cart_page(self, client):
        response = client.get(reverse("catalog:cart_detail"))
        assert response.status_code == 200
        assert "Кошик порожній." in response.content.decode()

    def test_cart_counter_is_shown_in_navbar(self, client, book):
        client.post(reverse("catalog:cart_add", args=[book.pk]))
        response = client.get(reverse("catalog:home"))
        assert response.context["cart_count"] == 1
        assert "(1)" in response.content.decode()


class TestBookWritePermissions:
    def test_anonymous_is_redirected_to_login(self, client):
        response = client.get(reverse("catalog:book_create"))
        assert response.status_code == 302
        assert response.url.startswith("/accounts/login/")

    def test_user_without_permission_gets_403(self, auth_client):
        response = auth_client.get(reverse("catalog:book_create"))
        assert response.status_code == 403
        assert "403.html" in template_names(response)

    def test_manager_sees_create_form(self, manager_client):
        response = manager_client.get(reverse("catalog:book_create"))
        assert response.status_code == 200
        assert "catalog/book_form.html" in template_names(response)

    def test_manager_creates_book(self, manager_client, category):
        data = {
            "title": "New",
            "author": "Author",
            "price": "50.00",
            "description": "",
            "stock": "3",
            "category": category.pk,
        }
        response = manager_client.post(reverse("catalog:book_create"), data)
        assert response.status_code == 302
        assert response.url == reverse("catalog:book_list")
        assert Book.objects.filter(title="New").exists()

    def test_invalid_form_is_redisplayed(self, manager_client, category):
        data = {"title": "Bad", "author": "A", "price": "0", "stock": "1", "category": category.pk}
        response = manager_client.post(reverse("catalog:book_create"), data)
        assert response.status_code == 200
        assert "price" in response.context["form"].errors
        assert not Book.objects.filter(title="Bad").exists()

    def test_manager_updates_book(self, manager_client, book):
        data = {
            "title": "Renamed",
            "author": book.author,
            "price": "10.00",
            "description": "",
            "stock": "1",
            "category": book.category_id,
        }
        response = manager_client.post(reverse("catalog:book_update", args=[book.pk]), data)
        assert response.status_code == 302
        assert response.url == reverse("catalog:book_detail", args=[book.pk])
        book.refresh_from_db()
        assert book.title == "Renamed"

    def test_manager_deletes_book(self, manager_client, book):
        response = manager_client.post(reverse("catalog:book_delete", args=[book.pk]))
        assert response.status_code == 302
        assert not Book.objects.filter(pk=book.pk).exists()

    def test_regular_user_cannot_delete(self, auth_client, book):
        response = auth_client.post(reverse("catalog:book_delete", args=[book.pk]))
        assert response.status_code == 403
        assert Book.objects.filter(pk=book.pk).exists()


class TestCheckoutView:
    def test_requires_login(self, client):
        response = client.post(reverse("catalog:checkout"), {"email": "a@example.com"})
        assert response.status_code == 302
        assert response.url.startswith("/accounts/login/")

    def test_empty_cart(self, auth_client):
        response = auth_client.post(reverse("catalog:checkout"), {"email": "a@example.com"})
        assert response.url == reverse("catalog:cart_detail")
        assert message_texts(response) == ["Кошик порожній."]

    @pytest.mark.parametrize(
        "email, expected",
        [("", "Вкажіть email для замовлення."), ("nope", "Вкажіть коректний email.")],
    )
    def test_email_validation(self, auth_client, book, email, expected):
        auth_client.post(reverse("catalog:cart_add", args=[book.pk]))
        response = auth_client.post(reverse("catalog:checkout"), {"email": email})
        assert response.url == reverse("catalog:cart_detail")
        assert message_texts(response) == [expected]
        assert Order.objects.count() == 0

    def test_stripe_not_configured(self, auth_client, book, settings):
        settings.STRIPE_SECRET_KEY = ""
        auth_client.post(reverse("catalog:cart_add", args=[book.pk]))
        response = auth_client.post(reverse("catalog:checkout"), {"email": "a@example.com"})
        assert message_texts(response) == ["Оплата Stripe ще не налаштована."]
        assert Order.objects.count() == 0

    def test_success_redirects_to_stripe(self, auth_client, book, stripe_session_create):
        auth_client.post(reverse("catalog:cart_add", args=[book.pk]))
        response = auth_client.post(reverse("catalog:checkout"), {"email": "a@example.com"})
        assert response.status_code == 302
        assert response.url == FAKE_STRIPE_URL
        order = Order.objects.get()
        assert order.stripe_session_id == "cs_test_123"
        assert auth_client.session["pending_order_id"] == order.pk
        assert auth_client.session["cart"] == {}
        stripe_session_create.assert_called_once()

    def test_stripe_failure_cancels_order_and_restores_stock(self, auth_client, book):
        auth_client.post(reverse("catalog:cart_add", args=[book.pk]))
        with mock.patch("stripe.checkout.Session.create", side_effect=RuntimeError("boom")):
            response = auth_client.post(reverse("catalog:checkout"), {"email": "a@example.com"})
        assert response.url == reverse("catalog:cart_detail")
        assert message_texts(response) == ["Не вдалося створити оплату. Спробуйте ще раз."]
        book.refresh_from_db()
        assert book.stock == 10
        assert Order.objects.get().status == Order.Status.CANCELLED

    def test_success_page_requires_login(self, client):
        assert client.get(reverse("catalog:checkout_success")).status_code == 302

    def test_success_page_without_session_id(self, auth_client):
        response = auth_client.get(reverse("catalog:checkout_success"))
        assert response.status_code == 200
        assert response.context["order"] is None

    def test_success_page_marks_order_paid_after_stripe_confirms(
        self, auth_client, user, make_order, stripe_paid_session
    ):
        order = make_order(user=user, stripe_session_id="cs_ok")
        response = auth_client.get(reverse("catalog:checkout_success"), {"session_id": "cs_ok"})
        assert response.context["order"] == order
        stripe_paid_session.assert_called_once_with("cs_ok")
        order.refresh_from_db()
        assert order.status == Order.Status.PAID

    def test_success_url_without_payment_does_not_mark_paid(
        self, auth_client, user, make_order, stripe_unpaid_session
    ):
        order = make_order(user=user, stripe_session_id="cs_unpaid")
        response = auth_client.get(
            reverse("catalog:checkout_success"), {"session_id": "cs_unpaid"}
        )
        assert response.status_code == 200
        assert response.context["order"] is None
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_success_url_of_another_user_is_ignored(
        self, auth_client, make_order, stripe_paid_session
    ):
        foreign = make_order(stripe_session_id="cs_foreign")
        response = auth_client.get(
            reverse("catalog:checkout_success"), {"session_id": "cs_foreign"}
        )
        assert response.context["order"] is None
        stripe_paid_session.assert_not_called()
        foreign.refresh_from_db()
        assert foreign.status == Order.Status.PENDING

    def test_already_paid_order_is_shown_without_calling_stripe(
        self, auth_client, user, make_order, stripe_paid_session
    ):
        order = make_order(user=user, stripe_session_id="cs_done", status=Order.Status.PAID)
        response = auth_client.get(reverse("catalog:checkout_success"), {"session_id": "cs_done"})
        assert response.context["order"] == order
        stripe_paid_session.assert_not_called()

    def test_cancel_without_pending_order(self, auth_client):
        response = auth_client.get(reverse("catalog:checkout_cancel"))
        assert response.url == reverse("catalog:cart_detail")
        assert message_texts(response) == ["Оплату скасовано."]


class TestStripeWebhook:
    URL = reverse_lazy("catalog:stripe_webhook")

    def post(self, client, **extra):
        return client.post(self.URL, data="{}", content_type="application/json", **extra)

    def test_without_secret_events_are_rejected(self, client, settings, make_order):
        settings.STRIPE_WEBHOOK_SECRET = ""
        order = make_order(stripe_session_id="cs_hook")
        with mock.patch("stripe.Webhook.construct_event") as construct:
            response = self.post(client)
        assert response.status_code == 400
        construct.assert_not_called()
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_only_post_is_allowed(self, client):
        assert client.get(self.URL).status_code == 405

    def test_invalid_payload_returns_400(self, client, stripe_webhook_event):
        stripe_webhook_event.side_effect = ValueError("bad json")
        response = self.post(client)
        assert response.status_code == 400
        assert response.json() == {"error": "invalid payload"}

    def test_bad_signature_returns_400(self, client, stripe_webhook_event, make_order):
        order = make_order(stripe_session_id="cs_hook")
        stripe_webhook_event.side_effect = stripe.SignatureVerificationError("bad", "sig")
        assert self.post(client).status_code == 400
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_real_signature_check_rejects_forged_event(self, client, make_order):
        order = make_order(stripe_session_id="cs_hook")
        forged = json.dumps(stripe_event("checkout.session.completed", "cs_hook"))
        response = client.post(
            self.URL, data=forged, content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=forged",
        )
        assert response.status_code == 400
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_completed_event_marks_order_paid(self, client, stripe_webhook_event, make_order):
        order = make_order(stripe_session_id="cs_hook")
        stripe_webhook_event.return_value = stripe_event("checkout.session.completed", "cs_hook")
        response = self.post(client, HTTP_STRIPE_SIGNATURE="t=1,v1=ok")
        assert response.status_code == 200
        payload, signature, secret = stripe_webhook_event.call_args.args
        assert (signature, secret) == ("t=1,v1=ok", "whsec_test")
        order.refresh_from_db()
        assert order.status == Order.Status.PAID

    def test_completed_but_unpaid_session_is_not_marked_paid(
        self, client, stripe_webhook_event, make_order
    ):
        order = make_order(stripe_session_id="cs_hook")
        stripe_webhook_event.return_value = stripe_event(
            "checkout.session.completed", "cs_hook", payment_status="unpaid"
        )
        assert self.post(client).status_code == 200
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_async_payment_succeeded_marks_paid(self, client, stripe_webhook_event, make_order):
        order = make_order(stripe_session_id="cs_hook")
        stripe_webhook_event.return_value = stripe_event(
            "checkout.session.async_payment_succeeded", "cs_hook"
        )
        self.post(client)
        order.refresh_from_db()
        assert order.status == Order.Status.PAID

    @pytest.mark.parametrize(
        "event_type", ["checkout.session.expired", "checkout.session.async_payment_failed"]
    )
    def test_expired_or_failed_session_cancels_order(
        self, client, stripe_webhook_event, make_order, make_order_item, make_book, event_type
    ):
        book = make_book(stock=0)
        order = make_order(stripe_session_id="cs_hook")
        make_order_item(order=order, book=book, quantity=3)
        stripe_webhook_event.return_value = stripe_event(event_type, "cs_hook", "unpaid")
        assert self.post(client).status_code == 200
        order.refresh_from_db()
        book.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
        assert book.stock == 3

    def test_other_events_are_ignored(self, client, stripe_webhook_event, make_order):
        order = make_order(stripe_session_id="cs_hook")
        stripe_webhook_event.return_value = stripe_event("charge.refunded", "cs_hook")
        assert self.post(client).status_code == 200
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING


class TestErrorPages:
    def test_unknown_url_renders_404_template(self, client):
        response = client.get("/definitely/not/here/")
        assert response.status_code == 404
        assert "404.html" in template_names(response)

    def test_server_error_view(self, rf):
        response = server_error(rf.get("/"))
        assert response.status_code == 500
        assert "500" in response.content.decode()
