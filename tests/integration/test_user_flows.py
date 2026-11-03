"""Наскрізні сценарії користувача: клієнт -> middleware -> в'ю -> ORM -> шаблон.

Зовнішні сервіси замінені mock-ами: Stripe - фікстура ``stripe_session_create``
і ``mock.patch``; email - locmem-бекенд (``mailoutbox``) та ``django_capture_on_commit_callbacks``.
"""

import re
from decimal import Decimal
from unittest import mock

import pytest
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.urls import reverse

from catalog.models import Book, Order
from tests.conftest import FAKE_STRIPE_URL, stripe_event
from tests.factories import BookFactory, CategoryFactory, DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

CYRILLIC = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")


def add_to_cart(client, book, times=1):
    for _ in range(times):
        client.post(reverse("catalog:cart_add", args=[book.pk]))


def checkout(client, email="buyer@example.com", **kwargs):
    return client.post(reverse("catalog:checkout"), {"email": email}, **kwargs)


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def assert_no_cyrillic(response):
    text = response.content.decode("utf-8")
    match = CYRILLIC.search(text)
    assert match is None, f"Знайдено кирилицю: ...{text[max(match.start() - 40, 0):match.end() + 40]}..."


def use_language(client, code):
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = code


# --------------------------------------------------------------------------- каталог


def test_visitor_browses_from_home_to_book_detail(client, make_book):
    book = make_book(title="Kobzar", author="Shevchenko", stock=3)
    home = client.get(reverse("catalog:home"))
    assert home.status_code == 200
    assert book.title in home.content.decode()

    listing = client.get(reverse("catalog:book_list"))
    assert reverse("catalog:book_detail", args=[book.pk]) in listing.content.decode()

    detail = client.get(reverse("catalog:book_detail", args=[book.pk]))
    content = detail.content.decode()
    assert detail.status_code == 200
    assert "Shevchenko" in content
    assert reverse("catalog:cart_add", args=[book.pk]) in content


def test_search_filter_and_pagination_flow(client, make_book, category):
    other_category = CategoryFactory()
    for i in range(6):
        make_book(title=f"Match {i}", category=category)
    make_book(title="Unique title", category=category)
    for i in range(2):
        make_book(title=f"Other {i}", category=other_category)

    url = reverse("catalog:book_list")
    first = client.get(url, {"q": "match"})
    assert first.context["page_obj"].paginator.count == 6
    assert first.context["is_paginated"] is True
    assert "Знайдено 6 книг" in first.content.decode()
    assert "?page=2&q=match" in first.content.decode()

    second = client.get(url, {"q": "match", "page": 2})
    assert len(second.context["books"]) == 2

    single = client.get(url, {"q": "unique"})
    assert "Знайдено 1 книгу" in single.content.decode()

    by_category = client.get(url, {"category": other_category.pk, "in_stock": "1"})
    assert sorted(b.title for b in by_category.context["books"]) == ["Other 0", "Other 1"]


def test_seeded_demo_catalog_can_be_browsed(client):
    call_command("seed_demo", verbosity=0)
    assert Book.objects.count() == 12

    page_three = client.get(reverse("catalog:book_list"), {"page": 3})
    assert page_three.status_code == 200
    assert len(page_three.context["books"]) == 4

    found = client.get(reverse("catalog:book_list"), {"q": "Кобзар"})
    assert [b.title for b in found.context["books"]] == ["Кобзар"]

    stats = client.get(reverse("catalog:api_stats")).json()
    assert stats["books_total"] == 12
    assert stats["categories_total"] == 3


# --------------------------------------------------------------------------- акаунти


def test_signup_creates_user_and_logs_in(client):
    page = client.get(reverse("account_signup"))
    assert page.status_code == 200

    response = client.post(
        reverse("account_signup"),
        {"username": "newreader", "password1": DEFAULT_PASSWORD, "password2": DEFAULT_PASSWORD},
    )
    assert response.status_code == 302
    user = get_user_model().objects.get(username="newreader")
    assert user.check_password(DEFAULT_PASSWORD)
    assert client.session["_auth_user_id"] == str(user.pk)


def test_signup_rejects_mismatched_passwords(client):
    response = client.post(
        reverse("account_signup"),
        {"username": "newreader", "password1": DEFAULT_PASSWORD, "password2": "Different-pass1!"},
    )
    assert response.status_code == 200
    assert not get_user_model().objects.filter(username="newreader").exists()


def test_login_and_logout_flow(client, user):
    response = client.post(reverse("account_login"), {"login": "reader", "password": DEFAULT_PASSWORD})
    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(user.pk)
    assert "reader" in client.get(reverse("catalog:home")).content.decode()

    response = client.post(reverse("account_logout"))
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


def test_login_with_wrong_password_is_rejected(client, user):
    response = client.post(reverse("account_login"), {"login": "reader", "password": "wrong-pass"})
    assert response.status_code == 200
    assert response.context["form"].errors
    assert "_auth_user_id" not in client.session


# --------------------------------------------------------------------------- кошик і оплата


def test_stock_limit_is_enforced_in_cart(client, make_book):
    book = make_book(stock=2)
    add_to_cart(client, book, times=3)
    assert client.session["cart"] == {str(book.pk): 2}
    page = client.get(reverse("catalog:cart_detail"))
    assert "disabled" in page.content.decode()


def test_anonymous_visitor_logs_in_and_pays(client, make_book, user, stripe_session_create):
    book = make_book(price=Decimal("80.00"), stock=4)
    add_to_cart(client, book, times=2)

    cart_page = client.get(reverse("catalog:cart_detail"))
    assert "/accounts/login/?next=/cart/" in cart_page.content.decode()

    anonymous_attempt = checkout(client)
    assert anonymous_attempt.status_code == 302
    assert anonymous_attempt.url.startswith("/accounts/login/")

    client.force_login(user)  # кошик у сесії зберігається після входу
    assert client.session["cart"] == {str(book.pk): 2}
    response = checkout(client)
    assert response.url == FAKE_STRIPE_URL
    assert Order.objects.get().total == Decimal("160.00")


def test_full_purchase_flow(
    auth_client,
    user,
    make_book,
    stripe_session_create,
    stripe_paid_session,
    django_capture_on_commit_callbacks,
    mailoutbox,
):
    first = make_book(title="First", price=Decimal("100.00"), stock=5)
    second = make_book(title="Second", price=Decimal("50.00"), stock=3)
    add_to_cart(auth_client, first, times=2)
    add_to_cart(auth_client, second)

    cart_page = auth_client.get(reverse("catalog:cart_detail"))
    assert cart_page.context["cart"].total == Decimal("250.00")

    with django_capture_on_commit_callbacks(execute=True):
        response = checkout(auth_client, email="buyer@example.com")
    assert response.status_code == 302
    assert response.url == FAKE_STRIPE_URL

    order = Order.objects.get()
    assert (order.user, order.email, order.total) == (user, "buyer@example.com", Decimal("250.00"))
    assert order.status == Order.Status.PENDING
    assert order.items.count() == 2
    first.refresh_from_db()
    second.refresh_from_db()
    assert (first.stock, second.stock) == (3, 2)
    assert auth_client.session["cart"] == {}

    assert mailoutbox == []  # до оплати листа немає

    with django_capture_on_commit_callbacks(execute=True):
        success = auth_client.get(
            reverse("catalog:checkout_success"), {"session_id": "cs_test_123"}
        )
    assert success.status_code == 200
    stripe_paid_session.assert_called_once_with("cs_test_123")
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["buyer@example.com"]
    assert str(order.pk) in mailoutbox[0].subject
    assert success.context["order"] == order
    assert f"#{order.pk}" in success.content.decode()
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    assert "pending_order_id" not in auth_client.session


def test_cancelled_payment_restores_stock(auth_client, make_book, stripe_session_create):
    book = make_book(stock=5)
    add_to_cart(auth_client, book, times=2)
    checkout(auth_client)
    book.refresh_from_db()
    assert book.stock == 3

    response = auth_client.get(reverse("catalog:checkout_cancel"))
    assert response.url == reverse("catalog:cart_detail")
    assert message_texts(response) == ["Оплату скасовано."]
    book.refresh_from_db()
    assert book.stock == 5
    assert Order.objects.get().status == Order.Status.CANCELLED
    assert "pending_order_id" not in auth_client.session


def test_stripe_outage_keeps_cart_and_stock(auth_client, make_book):
    book = make_book(stock=5)
    add_to_cart(auth_client, book)
    with mock.patch("stripe.checkout.Session.create", side_effect=stripe.APIConnectionError("down")):
        response = checkout(auth_client, follow=True)
    assert "Не вдалося створити оплату. Спробуйте ще раз." in response.content.decode()
    assert auth_client.session["cart"] == {str(book.pk): 1}
    book.refresh_from_db()
    assert book.stock == 5
    assert Order.objects.get().status == Order.Status.CANCELLED


def test_empty_cart_checkout_shows_error(auth_client):
    response = checkout(auth_client, follow=True)
    assert response.status_code == 200
    assert "Кошик порожній." in response.content.decode()
    assert Order.objects.count() == 0


def test_webhook_confirms_payment_without_browser_return(
    auth_client, client, make_book, stripe_session_create, stripe_webhook_event,
    django_capture_on_commit_callbacks, mailoutbox,
):
    add_to_cart(auth_client, make_book())
    checkout(auth_client)
    stripe_webhook_event.return_value = stripe_event("checkout.session.completed", "cs_test_123")
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("catalog:stripe_webhook"), "{}", content_type="application/json"
        )
    assert response.status_code == 200
    assert Order.objects.get().status == Order.Status.PAID
    assert len(mailoutbox) == 1


def test_webhook_signature_is_passed_to_stripe(client, settings, make_order):
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    order = make_order(stripe_session_id="cs_signed")
    event = stripe_event("checkout.session.completed", "cs_signed")
    with mock.patch("stripe.Webhook.construct_event", return_value=event) as construct:
        response = client.post(
            reverse("catalog:stripe_webhook"),
            "{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=abc",
        )
    assert response.status_code == 200
    _, signature, secret = construct.call_args.args
    assert (signature, secret) == ("t=1,v1=abc", "whsec_test")
    order.refresh_from_db()
    assert order.status == Order.Status.PAID


# --------------------------------------------------------------------------- права доступу


def test_manager_book_crud_flow(manager_client, category):
    listing = manager_client.get(reverse("catalog:book_list"))
    assert reverse("catalog:book_create") in listing.content.decode()

    created = manager_client.post(
        reverse("catalog:book_create"),
        {
            "title": "Flow book",
            "author": "Flow author",
            "price": "75.50",
            "description": "desc",
            "stock": "4",
            "category": category.pk,
        },
        follow=True,
    )
    assert created.redirect_chain[-1][0] == reverse("catalog:book_list")
    assert "Flow book" in created.content.decode()
    book = Book.objects.get(title="Flow book")
    assert book.price == Decimal("75.50")

    edit_page = manager_client.get(reverse("catalog:book_update", args=[book.pk]))
    assert edit_page.context["form"].initial["title"] == "Flow book"
    updated = manager_client.post(
        reverse("catalog:book_update", args=[book.pk]),
        {
            "title": "Flow book v2",
            "author": "Flow author",
            "price": "80.00",
            "description": "desc",
            "stock": "2",
            "category": category.pk,
        },
        follow=True,
    )
    assert updated.redirect_chain[-1][0] == reverse("catalog:book_detail", args=[book.pk])
    assert "Flow book v2" in updated.content.decode()

    confirm = manager_client.get(reverse("catalog:book_delete", args=[book.pk]))
    assert "Flow book v2" in confirm.content.decode()
    manager_client.post(reverse("catalog:book_delete", args=[book.pk]))
    assert not Book.objects.filter(pk=book.pk).exists()
    assert manager_client.get(reverse("catalog:book_detail", args=[book.pk])).status_code == 404


def test_manager_cannot_save_invalid_book(manager_client, category):
    response = manager_client.post(
        reverse("catalog:book_create"),
        {"title": "", "author": "A", "price": "-1", "stock": "1", "category": category.pk},
    )
    assert response.status_code == 200
    assert set(response.context["form"].errors) == {"title", "price"}
    assert Book.objects.count() == 0


def test_regular_user_cannot_change_catalog(auth_client, book):
    listing = auth_client.get(reverse("catalog:book_list"))
    content = listing.content.decode()
    assert reverse("catalog:book_create") not in content
    assert reverse("catalog:book_update", args=[book.pk]) not in content

    urls = [
        reverse("catalog:book_create"),
        reverse("catalog:book_update", args=[book.pk]),
        reverse("catalog:book_delete", args=[book.pk]),
    ]
    assert [auth_client.get(url).status_code for url in urls] == [403, 403, 403]
    assert auth_client.post(urls[2]).status_code == 403
    assert Book.objects.filter(pk=book.pk).exists()


def test_anonymous_visitor_is_sent_to_login_for_protected_pages(client, book):
    protected = [
        reverse("catalog:book_create"),
        reverse("catalog:book_update", args=[book.pk]),
        reverse("catalog:book_delete", args=[book.pk]),
        reverse("catalog:checkout_success"),
        reverse("catalog:checkout_cancel"),
    ]
    for url in protected:
        response = client.get(url)
        assert response.status_code == 302, url
        assert response.url.startswith("/accounts/login/"), url


def test_superuser_can_open_admin_pages(client):
    admin = get_user_model().objects.create_superuser("root", "root@example.com", "Adm1n-pass!")
    client.force_login(admin)
    CategoryFactory()
    BookFactory()
    for url in [
        "/admin/",
        "/admin/catalog/book/",
        "/admin/catalog/book/add/",
        "/admin/catalog/category/",
        "/admin/catalog/order/",
        "/admin/accounts/customuser/",
    ]:
        assert client.get(url).status_code == 200, url


# --------------------------------------------------------------------------- мови


def test_language_switcher_flow(client, make_book):
    make_book(title="English title")
    assert "Каталог книг" in client.get(reverse("catalog:book_list")).content.decode()

    switched = client.post(reverse("set_language"), {"language": "en", "next": "/books/"})
    assert switched.status_code == 302
    assert switched.url == "/books/"
    assert client.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"

    english = client.get("/books/")
    content = english.content.decode()
    assert "Book catalog" in content
    assert '<html lang="en">' in content
    assert_no_cyrillic(english)

    client.post(reverse("set_language"), {"language": "uk", "next": "/books/"})
    ukrainian = client.get("/books/")
    assert "Каталог книг" in ukrainian.content.decode()
    assert '<html lang="uk">' in ukrainian.content.decode()


def test_accept_language_header_selects_language(client):
    assert "Browse the catalog" in client.get("/", HTTP_ACCEPT_LANGUAGE="en").content.decode()
    assert "Дивитися каталог" in client.get("/", HTTP_ACCEPT_LANGUAGE="uk").content.decode()
    assert "Дивитися каталог" in client.get("/", HTTP_ACCEPT_LANGUAGE="fr").content.decode()


def test_english_site_has_no_untranslated_text(auth_client, make_book):
    book = make_book(title="English title", stock=2)
    add_to_cart(auth_client, book)
    use_language(auth_client, "en")
    pages = [
        reverse("catalog:home"),
        reverse("catalog:book_list"),
        reverse("catalog:book_list_fbv"),
        reverse("catalog:book_detail", args=[book.pk]),
        reverse("catalog:cart_detail"),
        "/this/page/does/not/exist/",
    ]
    for url in pages:
        assert_no_cyrillic(auth_client.get(url))


def test_english_anonymous_pages_have_no_untranslated_text(client):
    use_language(client, "en")
    for url in [reverse("catalog:cart_detail"), reverse("account_login"), reverse("account_signup")]:
        assert_no_cyrillic(client.get(url))


def test_english_messages_and_validation_errors(auth_client, make_book):
    use_language(auth_client, "en")
    response = checkout(auth_client)
    assert message_texts(response) == ["Your cart is empty."]
    add_to_cart(auth_client, make_book())
    response = checkout(auth_client, email="")
    # перше повідомлення ще не показане на сторінці, тому в черзі лишається і воно
    assert message_texts(response)[-1] == "Please enter an email for the order."


# --------------------------------------------------------------------------- async API


def test_async_api_reflects_a_purchase(auth_client, user, make_book, stripe_session_create):
    book = make_book(title="Async flow", price=Decimal("120.00"), stock=5)
    before = auth_client.get(reverse("catalog:api_stats")).json()
    assert before["total_stock"] == 5

    add_to_cart(auth_client, book, times=2)
    checkout(auth_client)

    after = auth_client.get(reverse("catalog:api_stats")).json()
    assert after["total_stock"] == 3

    orders = auth_client.get(reverse("catalog:api_orders")).json()
    assert orders["count"] == 1
    assert orders["results"][0]["items_count"] == 1
    assert orders["results"][0]["status"] == "pending"
    assert orders["results"][0]["total"] == "240.00"

    found = auth_client.get(reverse("catalog:api_books"), {"q": "async"}).json()
    assert [r["stock"] for r in found["results"]] == [3]

    category = auth_client.get(reverse("catalog:api_category", args=[book.category.slug])).json()
    assert [b["title"] for b in category["books"]] == ["Async flow"]


def test_async_orders_endpoint_requires_login(client):
    other = UserFactory()
    assert client.get(reverse("catalog:api_orders")).status_code == 401
    client.force_login(other)
    assert client.get(reverse("catalog:api_orders")).json() == {"count": 0, "results": []}


def test_book_data_is_translated_in_english(client, make_book):
    book = make_book(
        title="Кобзар", author="Тарас Шевченко", description="Збірка поезій",
        title_en="Kobzar", author_en="Taras Shevchenko", description_en="A collection of poems",
        stock=2,
    )
    book.category.name, book.category.name_en = "Художня", "Fiction"
    book.category.save()
    use_language(client, "en")
    for url in [
        reverse("catalog:home"),
        reverse("catalog:book_list"),
        reverse("catalog:book_detail", args=[book.pk]),
    ]:
        response = client.get(url)
        assert "Kobzar" in response.content.decode()
        assert_no_cyrillic(response)
    use_language(client, "uk")
    assert "Кобзар" in client.get(reverse("catalog:book_detail", args=[book.pk])).content.decode()


def test_seeded_demo_catalog_is_fully_english_in_english(client):
    call_command("seed_demo", verbosity=0)
    use_language(client, "en")
    for page in (1, 2, 3):
        assert_no_cyrillic(client.get(reverse("catalog:book_list"), {"page": page}))
    book = Book.objects.get(title="Кобзар")
    detail = client.get(reverse("catalog:book_detail", args=[book.pk]))
    assert "Kobzar" in detail.content.decode()
    assert_no_cyrillic(detail)
    assert "Kobzar" in client.get(reverse("catalog:book_list"), {"q": "kobzar"}).content.decode()


def test_manager_can_save_english_texts(manager_client, category):
    manager_client.post(
        reverse("catalog:book_create"),
        {
            "title": "Книга", "author": "Автор", "price": "10.00", "stock": "1",
            "category": category.pk, "title_en": "Book", "author_en": "Author",
            "description_en": "About the book",
        },
    )
    book = Book.objects.get(title="Книга")
    assert (book.title_en, book.author_en, book.description_en) == ("Book", "Author", "About the book")


def test_forged_success_url_does_not_give_free_order(
    auth_client, make_book, stripe_session_create, stripe_unpaid_session, mailoutbox
):
    """Користувач бачить session_id у адресі Stripe, але без оплати замовлення не стає оплаченим."""
    add_to_cart(auth_client, make_book())
    checkout(auth_client)
    response = auth_client.get(reverse("catalog:checkout_success"), {"session_id": "cs_test_123"})
    assert response.status_code == 200
    assert response.context["order"] is None
    assert Order.objects.get().status == Order.Status.PENDING
    assert mailoutbox == []
    # після цього ще можна скасувати оплату й повернути книги на склад
    auth_client.get(reverse("catalog:checkout_cancel"))
    assert Order.objects.get().status == Order.Status.CANCELLED


def test_abandoned_checkout_is_released_by_expired_webhook(
    auth_client, client, make_book, stripe_session_create, stripe_webhook_event
):
    book = make_book(stock=2)
    add_to_cart(auth_client, book, times=2)
    checkout(auth_client)
    book.refresh_from_db()
    assert book.stock == 0

    stripe_webhook_event.return_value = stripe_event(
        "checkout.session.expired", "cs_test_123", payment_status="unpaid"
    )
    client.post(reverse("catalog:stripe_webhook"), "{}", content_type="application/json")
    book.refresh_from_db()
    assert book.stock == 2
    assert Order.objects.get().status == Order.Status.CANCELLED


def test_stale_orders_command_releases_stock(auth_client, make_book, stripe_session_create):
    from datetime import timedelta
    from io import StringIO

    from django.utils import timezone

    book = make_book(stock=1)
    add_to_cart(auth_client, book)
    checkout(auth_client)
    Order.objects.update(created_at=timezone.now() - timedelta(hours=48))
    out = StringIO()
    call_command("cancel_stale_orders", "--hours", "24", stdout=out)
    assert "1" in out.getvalue()
    book.refresh_from_db()
    assert book.stock == 1
    assert Order.objects.get().status == Order.Status.CANCELLED


def test_book_form_shows_categories_in_english(manager_client, category):
    category.name, category.name_en = "Художня", "Fiction"
    category.save()
    use_language(manager_client, "en")
    form_page = manager_client.get(reverse("catalog:book_create"))
    content = form_page.content.decode()
    assert ">Fiction</option>" in content
    assert "Художня" not in content


TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def test_manager_uploads_cover_and_it_is_shown(manager_client, category, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    response = manager_client.post(
        reverse("catalog:book_create"),
        {
            "title": "З обкладинкою", "author": "Автор", "price": "10.00", "stock": "1",
            "category": category.pk,
            "cover": SimpleUploadedFile("cover.gif", TINY_GIF, content_type="image/gif"),
        },
    )
    assert response.status_code == 302
    book = Book.objects.get(title="З обкладинкою")
    assert book.cover.name.startswith("covers/")
    assert (tmp_path / book.cover.name).is_file()
    detail = manager_client.get(reverse("catalog:book_detail", args=[book.pk]))
    assert book.cover.url in detail.content.decode()


def test_manager_cannot_upload_non_image(manager_client, category, settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    response = manager_client.post(
        reverse("catalog:book_create"),
        {
            "title": "Погана", "author": "Автор", "price": "10.00", "stock": "1",
            "category": category.pk,
            "cover": SimpleUploadedFile("cover.jpg", b"not an image", content_type="image/jpeg"),
        },
    )
    assert response.status_code == 200
    assert "cover" in response.context["form"].errors
    assert not Book.objects.filter(title="Погана").exists()


def test_book_without_cover_shows_placeholder(client, make_book):
    book = make_book(pk=99999)
    content = client.get(reverse("catalog:book_detail", args=[book.pk])).content.decode()
    assert "img/books/placeholder.svg" in content


def test_catalog_is_sorted_by_english_title_in_english(client, make_book):
    make_book(title="Аліса", title_en="Alice")
    make_book(title="Гаррі", title_en="Harry")
    make_book(title="Енеїда", title_en="Eneida")
    make_book(title="Без перекладу")
    use_language(client, "en")
    titles = [b.title_en or b.title for b in client.get(reverse("catalog:book_list")).context["books"]]
    assert titles == ["Alice", "Eneida", "Harry", "Без перекладу"]
    use_language(client, "uk")
    titles = [b.title for b in client.get(reverse("catalog:book_list")).context["books"]]
    assert titles == ["Аліса", "Без перекладу", "Гаррі", "Енеїда"]
