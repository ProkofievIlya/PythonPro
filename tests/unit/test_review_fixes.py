"""Тести для правок після AI code review (checkout, checkout_success, stripe_webhook)."""

from unittest import mock

import pytest
from django.urls import reverse

from catalog import views
from catalog.models import Order

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


def test_checkout_failure_is_logged(auth_client, book):
    # Generated with AI, reviewed and modified
    auth_client.post(reverse("catalog:cart_add", args=[book.pk]))
    with mock.patch("stripe.checkout.Session.create", side_effect=RuntimeError("boom")):
        with mock.patch.object(views.logger, "exception") as log_exception:
            auth_client.post(reverse("catalog:checkout"), {"email": "a@example.com"})
    log_exception.assert_called_once()


def test_webhook_event_without_session_id_is_ignored(client, stripe_webhook_event):
    # Generated with AI, reviewed and modified
    stripe_webhook_event.return_value = {
        "type": "checkout.session.completed",
        "data": {"object": {"payment_status": "paid"}},
    }
    response = client.post(
        reverse("catalog:stripe_webhook"), data="{}", content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}


def test_webhook_for_unknown_order_is_logged(client, stripe_webhook_event):
    # Generated with AI, reviewed and modified
    stripe_webhook_event.return_value = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_unknown", "payment_status": "paid"}},
    }
    with mock.patch.object(views.logger, "warning") as log_warning:
        response = client.post(
            reverse("catalog:stripe_webhook"), data="{}", content_type="application/json"
        )
    assert response.status_code == 200
    log_warning.assert_called_once()


def test_webhook_unrelated_event_returns_ok(client, stripe_webhook_event, make_order):
    # Generated with AI, reviewed and modified
    order = make_order(stripe_session_id="cs_other")
    stripe_webhook_event.return_value = {
        "type": "customer.created",
        "data": {"object": {"id": "cs_other"}},
    }
    response = client.post(
        reverse("catalog:stripe_webhook"), data="{}", content_type="application/json"
    )
    assert response.json() == {"status": "ok"}
    order.refresh_from_db()
    assert order.status == Order.Status.PENDING
