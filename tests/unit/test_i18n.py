"""Інтернаціоналізація: каталоги .po/.mo, моделі, форми, шаблони, множина."""

import gettext as py_gettext
import re
from decimal import Decimal

import pytest
from django.conf import settings
from django.template import Context, Template
from django.utils import translation
from django.utils.translation import gettext, ngettext, pgettext

from catalog import checkout
from catalog.forms import BookForm, CheckoutForm
from catalog.models import Book, Category, Order
from scripts.compile_messages import parse_po
from tests.factories import BookFactory, OrderFactory, OrderItemFactory

LOCALE_DIR = settings.LOCALE_PATHS[0]
PLACEHOLDER = re.compile(r"%\((\w+)\)s")


def po_path(lang):
    return LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"


def mo_path(lang):
    return LOCALE_DIR / lang / "LC_MESSAGES" / "django.mo"


class TestSettings:
    def test_supported_languages(self):
        assert [code for code, _ in settings.LANGUAGES] == ["uk", "en"]
        assert settings.LANGUAGE_CODE == "uk"

    def test_locale_middleware_is_enabled(self):
        assert "django.middleware.locale.LocaleMiddleware" in settings.MIDDLEWARE


class TestCatalogFiles:
    @pytest.mark.parametrize("lang", ["uk", "en"])
    def test_po_and_mo_exist(self, lang):
        assert po_path(lang).is_file()
        assert mo_path(lang).is_file()

    @pytest.mark.parametrize("lang", ["uk", "en"])
    def test_every_entry_is_translated_with_same_placeholders(self, lang):
        messages = parse_po(po_path(lang).read_text(encoding="utf-8"))
        entries = {k: v for k, v in messages.items() if k != b""}
        assert len(entries) > 100
        for key, value in entries.items():
            msgid = key.split(b"\x04")[-1].split(b"\0")[0].decode()
            forms = value.decode().split("\0")
            assert all(forms), f"порожній переклад: {msgid!r}"
            for form in forms:
                assert set(PLACEHOLDER.findall(form)) == set(PLACEHOLDER.findall(msgid)), msgid

    @pytest.mark.parametrize("lang", ["uk", "en"])
    def test_compiled_mo_matches_po(self, lang):
        messages = parse_po(po_path(lang).read_text(encoding="utf-8"))
        with open(mo_path(lang), "rb") as handle:
            catalog = py_gettext.GNUTranslations(handle)._catalog
        for key, value in messages.items():
            if key == b"" or b"\0" in key:
                continue
            assert catalog[key.decode()] == value.decode()


class TestGettext:
    @pytest.mark.parametrize(
        "msgid, english",
        [
            ("Каталог", "Catalog"),
            ("Кошик", "Cart"),
            ("Оплачено", "Paid"),
            ("Кошик порожній.", "Your cart is empty."),
            ("Увійти", "Log in"),
        ],
    )
    def test_translates_to_english(self, msgid, english):
        with translation.override("en"):
            assert gettext(msgid) == english

    def test_ukrainian_is_the_source_language(self):
        with translation.override("uk"):
            assert gettext("Каталог") == "Каталог"

    def test_context_disambiguates_same_word(self):
        with translation.override("en"):
            assert pgettext("book title", "Назва") == "Title"
            assert pgettext("category name", "Назва") == "Name"

    @pytest.mark.parametrize(
        "lang, count, expected",
        [
            ("en", 1, "1 book found"),
            ("en", 2, "2 books found"),
            ("uk", 1, "Знайдено 1 книгу"),
            ("uk", 2, "Знайдено 2 книги"),
            ("uk", 5, "Знайдено 5 книг"),
            ("uk", 11, "Знайдено 11 книг"),
            ("uk", 21, "Знайдено 21 книгу"),
        ],
    )
    def test_plural_forms(self, lang, count, expected):
        with translation.override(lang):
            text = ngettext(
                "Знайдено %(counter)s книгу", "Знайдено %(counter)s книг", count
            )
        assert text % {"counter": count} == expected


class TestModelsAreTranslated:
    def test_verbose_names(self):
        with translation.override("en"):
            assert str(Book._meta.verbose_name) == "Book"
            assert str(Book._meta.verbose_name_plural) == "Books"
            assert str(Category._meta.verbose_name_plural) == "Categories"
            assert str(Order._meta.verbose_name) == "Order"
            assert str(Order._meta.verbose_name_plural) == "Orders"

    def test_same_ukrainian_word_has_different_english_field_names(self):
        with translation.override("en"):
            assert str(Book._meta.get_field("title").verbose_name) == "Title"
            assert str(Category._meta.get_field("name").verbose_name) == "Name"

    def test_ukrainian_verbose_names_are_unchanged(self):
        with translation.override("uk"):
            assert str(Book._meta.verbose_name) == "Книга"
            assert str(Book._meta.get_field("price").verbose_name) == "Ціна"

    def test_status_labels(self):
        with translation.override("en"):
            assert str(Order.Status.PENDING.label) == "Awaiting payment"
            assert str(Order.Status.PAID.label) == "Paid"
            assert str(Order.Status.CANCELLED.label) == "Cancelled"
        with translation.override("uk"):
            assert str(Order.Status.PAID.label) == "Оплачено"

    @pytest.mark.django_db
    def test_order_str_is_translated(self):
        order = OrderFactory()
        with translation.override("en"):
            assert str(order) == f"Order #{order.pk}"
        with translation.override("uk"):
            assert str(order) == f"Замовлення #{order.pk}"


@pytest.mark.django_db
class TestFormsAreTranslated:
    def test_model_form_labels(self):
        with translation.override("en"):
            form = BookForm()
            assert form.fields["title"].label == "Title"
            assert form.fields["price"].label == "Price"

    def test_checkout_form_errors(self):
        with translation.override("en"):
            required = CheckoutForm(data={"email": ""}).errors["email"][0]
            invalid = CheckoutForm(data={"email": "x"}).errors["email"][0]
        assert required == "Please enter an email for the order."
        assert invalid == "Please enter a valid email address."

    def test_price_error(self):
        form_data = {"title": "t", "author": "a", "price": "0", "stock": "1", "category": ""}
        with translation.override("en"):
            form = BookForm(data=form_data)
            assert "Price must be greater than zero." in form.errors["price"]


class TestTemplatesAreTranslated:
    TEMPLATE = (
        "{% load i18n %}"
        "{% blocktrans count counter=n %}Знайдено {{ counter }} книгу"
        "{% plural %}Знайдено {{ counter }} книг{% endblocktrans %}"
    )

    @pytest.mark.parametrize(
        "lang, n, expected",
        [("en", 1, "1 book found"), ("en", 3, "3 books found"), ("uk", 3, "Знайдено 3 книги")],
    )
    def test_blocktrans_plural(self, lang, n, expected):
        with translation.override(lang):
            assert Template(self.TEMPLATE).render(Context({"n": n})) == expected

    def test_blocktrans_with_variables(self):
        template = Template(
            "{% load i18n %}{% blocktrans with total=total %}Разом: {{ total }} ₴{% endblocktrans %}"
        )
        with translation.override("en"):
            assert template.render(Context({"total": 5})) == "Total: 5 ₴"


@pytest.mark.django_db
def test_order_email_is_sent_in_active_language(mailoutbox):
    order = OrderFactory(email="buyer@example.com", total=Decimal("10.00"))
    OrderItemFactory(order=order, price=Decimal("10.00"), quantity=1)
    with translation.override("en"):
        checkout.send_order_email(order.pk)
    message = mailoutbox[0]
    assert message.subject == f"Order #{order.pk}"
    assert "Total:" in message.body


@pytest.mark.django_db
def test_book_factory_still_works_under_english():
    with translation.override("en"):
        assert str(BookFactory(title="X", author="Y")) == "X — Y"
