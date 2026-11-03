from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.urls import reverse

from catalog.models import Book, Category


@pytest.mark.django_db
class TestRequestLogMiddleware:
    def test_logs_anonymous_request(self, client):
        with mock.patch("bookstore.middleware.logger") as logger:
            client.get(reverse("catalog:home"))
        args = logger.info.call_args.args
        assert args[1:5] == ("GET", "/", 200, "anonymous")

    def test_logs_authenticated_username(self, auth_client):
        with mock.patch("bookstore.middleware.logger") as logger:
            auth_client.get(reverse("catalog:home"))
        assert logger.info.call_args.args[4] == "reader"


@pytest.mark.django_db
class TestSeedDemoCommand:
    def test_creates_categories_and_books(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        assert Category.objects.count() == 3
        assert Book.objects.count() == 12
        assert "Готово" in out.getvalue()

    def test_is_idempotent(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        assert Book.objects.count() == 12
