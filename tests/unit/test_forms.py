from decimal import Decimal

import pytest
from django.urls import reverse

from accounts.forms import StyledLoginForm, StyledSignupForm
from catalog.forms import BookForm, CheckoutForm
from catalog.models import Book
from tests.factories import CategoryFactory


@pytest.fixture
def valid_data(db):
    category = CategoryFactory()
    return {
        "title": "Kobzar",
        "author": "Taras Shevchenko",
        "price": "199.00",
        "description": "Poems",
        "stock": "5",
        "category": category.pk,
    }


@pytest.mark.django_db
class TestBookForm:
    def test_valid_data(self, valid_data):
        form = BookForm(data=valid_data)
        assert form.is_valid(), form.errors

    def test_save_creates_book(self, valid_data):
        form = BookForm(data=valid_data)
        book = form.save()
        assert Book.objects.get(pk=book.pk).price == Decimal("199.00")

    @pytest.mark.parametrize("field", ["title", "author", "price", "stock", "category"])
    def test_required_fields(self, valid_data, field):
        valid_data.pop(field)
        form = BookForm(data=valid_data)
        assert not form.is_valid()
        assert field in form.errors

    def test_description_is_optional(self, valid_data):
        valid_data["description"] = ""
        assert BookForm(data=valid_data).is_valid()

    @pytest.mark.parametrize("price", ["0", "0.00", "-5"])
    def test_price_must_be_positive(self, valid_data, price):
        valid_data["price"] = price
        form = BookForm(data=valid_data)
        assert not form.is_valid()
        assert form.errors["price"][0]
        assert "invalid_price" in [e.code for e in form.errors.as_data()["price"]]

    def test_price_allows_only_two_decimal_places(self, valid_data):
        valid_data["price"] = "10.123"
        assert "price" in BookForm(data=valid_data).errors

    def test_stock_cannot_be_negative(self, valid_data):
        valid_data["stock"] = "-1"
        assert "stock" in BookForm(data=valid_data).errors

    def test_unknown_category_is_rejected(self, valid_data):
        valid_data["category"] = 999999
        assert "category" in BookForm(data=valid_data).errors

    def test_widgets_use_bootstrap_classes(self):
        form = BookForm()
        assert form.fields["title"].widget.attrs["class"] == "form-control"
        assert form.fields["category"].widget.attrs["class"] == "form-select"

    def test_fields_and_order(self):
        assert list(BookForm().fields) == [
            "title",
            "author",
            "price",
            "description",
            "stock",
            "category",
            "title_en",
            "author_en",
            "description_en",
            "cover",
        ]


class TestCheckoutForm:
    def test_valid_email(self):
        form = CheckoutForm(data={"email": "buyer@example.com"})
        assert form.is_valid()
        assert form.cleaned_data["email"] == "buyer@example.com"

    def test_email_is_required(self):
        form = CheckoutForm(data={"email": ""})
        assert not form.is_valid()
        assert form.errors["email"] == ["Вкажіть email для замовлення."]

    def test_email_must_be_valid(self):
        form = CheckoutForm(data={"email": "not-an-email"})
        assert not form.is_valid()
        assert form.errors["email"] == ["Вкажіть коректний email."]


@pytest.mark.django_db
class TestAccountForms:
    """Форми allauth беремо з реальних сторінок: так перевіряється і ACCOUNT_FORMS."""

    def test_login_page_uses_styled_form(self, client):
        form = client.get(reverse("account_login")).context["form"]
        assert isinstance(form, StyledLoginForm)
        assert all(f.widget.attrs["class"] == "form-control" for f in form.fields.values())

    def test_signup_page_uses_styled_form(self, client):
        form = client.get(reverse("account_signup")).context["form"]
        assert isinstance(form, StyledSignupForm)
        assert "username" in form.fields
        assert all(f.widget.attrs["class"] == "form-control" for f in form.fields.values())
