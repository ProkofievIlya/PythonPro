"""API-тести (DRF + JWT) на APIClient: книги, категорії, кошик, замовлення, права, CORS, документація."""

from decimal import Decimal
from unittest import mock

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from catalog.api.permissions import IsOwnerOrReadOnly
from catalog.api.throttles import TokenObtainThrottle
from catalog.models import Book, Cart, CartItem, Category, Order
from tests.factories import DEFAULT_PASSWORD, CategoryFactory, OrderItemFactory, UserFactory


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin(db):
    return UserFactory(username="admin", is_staff=True, is_superuser=True)


@pytest.fixture
def other(db):
    return UserFactory(username="other", email="other@example.com")


def as_user(api, user):
    api.force_authenticate(user)
    return api


# ---------------------------------------------------------------- JWT ---


def test_token_obtain_returns_access_and_refresh(api, user):
    r = api.post(reverse("token_obtain_pair"), {"username": user.username, "password": DEFAULT_PASSWORD})
    assert r.status_code == 200
    assert {"access", "refresh"} <= set(r.data)


def test_token_obtain_wrong_password(api, user):
    r = api.post(reverse("token_obtain_pair"), {"username": user.username, "password": "nope"})
    assert r.status_code == 401


def test_token_refresh_gives_new_access(api, user):
    tokens = api.post(
        reverse("token_obtain_pair"), {"username": user.username, "password": DEFAULT_PASSWORD}
    ).data
    r = api.post(reverse("token_refresh"), {"refresh": tokens["refresh"]})
    assert r.status_code == 200 and "access" in r.data


def test_token_verify_valid_and_invalid(api, user):
    access = api.post(
        reverse("token_obtain_pair"), {"username": user.username, "password": DEFAULT_PASSWORD}
    ).data["access"]
    assert api.post(reverse("token_verify"), {"token": access}).status_code == 200
    assert api.post(reverse("token_verify"), {"token": "garbage"}).status_code == 401


def test_bearer_token_authenticates_requests(api, user):
    access = api.post(
        reverse("token_obtain_pair"), {"username": user.username, "password": DEFAULT_PASSWORD}
    ).data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api.get(reverse("api:cart-list")).status_code == 200


@pytest.mark.parametrize("name", ["api:order-list", "api:cart-list", "api:cart-item-list"])
def test_protected_endpoints_require_token(api, name):
    assert api.get(reverse(name)).status_code == 401


# ------------------------------------------------------------- Books ---


def test_book_list_is_public_and_paginated(api, book):
    r = api.get(reverse("api:book-list"))
    assert r.status_code == 200
    assert {"count", "next", "previous", "results"} <= set(r.data)
    assert r.data["results"][0]["category"]["slug"] == "fiction"


def test_book_list_page_size_is_20(api, make_book):
    for _ in range(25):
        make_book()
    page1 = api.get(reverse("api:book-list")).data
    page2 = api.get(reverse("api:book-list"), {"page": 2}).data
    assert page1["count"] == 25 and len(page1["results"]) == 20 and page1["next"]
    assert len(page2["results"]) == 5 and page2["next"] is None


def test_book_detail(api, book):
    r = api.get(reverse("api:book-detail", args=[book.pk]))
    assert r.status_code == 200 and r.data["title"] == "Kobzar" and r.data["in_stock"] is True


def test_book_filter_by_category_slug(api, make_book):
    other_cat = CategoryFactory(name="Poetry", slug="poetry")
    make_book(title="Prose")
    make_book(title="Verse", category=other_cat)
    r = api.get(reverse("api:book-list"), {"category": "poetry"})
    assert [b["title"] for b in r.data["results"]] == ["Verse"]


def test_book_filter_by_price_range(api, make_book):
    make_book(title="Cheap", price=Decimal("50"))
    make_book(title="Mid", price=Decimal("150"))
    make_book(title="Dear", price=Decimal("500"))
    r = api.get(reverse("api:book-list"), {"min_price": 100, "max_price": 200})
    assert [b["title"] for b in r.data["results"]] == ["Mid"]


def test_book_filter_in_stock(api, make_book):
    make_book(title="Have", stock=3)
    make_book(title="Gone", stock=0)
    assert [b["title"] for b in api.get(reverse("api:book-list"), {"in_stock": "true"}).data["results"]] == ["Have"]
    assert [b["title"] for b in api.get(reverse("api:book-list"), {"in_stock": "false"}).data["results"]] == ["Gone"]


def test_book_filter_by_author(api, make_book):
    make_book(title="A", author="Lesya Ukrainka")
    make_book(title="B", author="Ivan Franko")
    r = api.get(reverse("api:book-list"), {"author": "franko"})
    assert [b["title"] for b in r.data["results"]] == ["B"]


def test_book_search(api, make_book):
    make_book(title="Zakhar Berkut", author="Franko")
    make_book(title="Other", author="Someone")
    r = api.get(reverse("api:book-list"), {"search": "berkut"})
    assert r.data["count"] == 1


def test_book_ordering_by_price_desc(api, make_book):
    make_book(title="A", price=Decimal("10"))
    make_book(title="B", price=Decimal("30"))
    r = api.get(reverse("api:book-list"), {"ordering": "-price"})
    assert [b["title"] for b in r.data["results"]] == ["B", "A"]


def test_book_create_requires_authentication(api, category):
    r = api.post(reverse("api:book-list"), {"title": "X", "author": "Y", "price": "10", "category_id": category.pk})
    assert r.status_code == 401


def test_book_create_forbidden_for_regular_user(api, user, category):
    r = as_user(api, user).post(
        reverse("api:book-list"), {"title": "X", "author": "Y", "price": "10", "category_id": category.pk}
    )
    assert r.status_code == 403


def test_book_create_by_admin(api, admin, category):
    payload = {"title": "New", "author": "Auth", "price": "99.50", "stock": 4, "category_id": category.pk}
    r = as_user(api, admin).post(reverse("api:book-list"), payload, format="json")
    assert r.status_code == 201
    assert r.data["category"]["id"] == category.pk
    assert Book.objects.get(pk=r.data["id"]).price == Decimal("99.50")


def test_book_create_rejects_non_positive_price(api, admin, category):
    r = as_user(api, admin).post(
        reverse("api:book-list"), {"title": "X", "author": "Y", "price": "0", "category_id": category.pk}
    )
    assert r.status_code == 400 and "price" in r.data


def test_book_patch_and_delete_by_admin(api, admin, book):
    as_user(api, admin)
    url = reverse("api:book-detail", args=[book.pk])
    assert api.patch(url, {"stock": 77}, format="json").data["stock"] == 77
    assert api.delete(url).status_code == 204
    assert not Book.objects.filter(pk=book.pk).exists()


def test_book_in_order_cannot_be_deleted(api, admin, book):
    OrderItemFactory(book=book)
    r = as_user(api, admin).delete(reverse("api:book-detail", args=[book.pk]))
    assert r.status_code == 409 and Book.objects.filter(pk=book.pk).exists()


# -------------------------------------------------------- Categories ---


def test_category_list_has_books_count(api, category, make_book):
    make_book()
    make_book()
    r = api.get(reverse("api:category-list"))
    assert r.status_code == 200 and r.data["results"][0]["books_count"] == 2


def test_category_detail_nests_books(api, category, make_book):
    make_book(title="Nested")
    r = api.get(reverse("api:category-detail", args=[category.pk]))
    assert r.data["books"][0]["title"] == "Nested"


def test_category_filter_by_name(api, db):
    CategoryFactory(name="Science", slug="science")
    CategoryFactory(name="History", slug="history")
    r = api.get(reverse("api:category-list"), {"name": "sci"})
    assert [c["slug"] for c in r.data["results"]] == ["science"]


def test_category_create_admin_only(api, user, admin):
    payload = {"name": "Comics", "slug": "comics"}
    assert as_user(api, user).post(reverse("api:category-list"), payload).status_code == 403
    assert as_user(api, admin).post(reverse("api:category-list"), payload).status_code == 201
    assert Category.objects.filter(slug="comics").exists()


# -------------------------------------------------------------- Cart ---


def test_cart_is_created_empty_on_first_get(api, user):
    r = as_user(api, user).get(reverse("api:cart-list"))
    assert r.status_code == 200 and r.data["items"] == [] and r.data["total"] == "0.00"
    assert Cart.objects.filter(user=user).exists()


def test_cart_add_item(api, user, book):
    r = as_user(api, user).post(reverse("api:cart-item-list"), {"book_id": book.pk, "quantity": 2}, format="json")
    assert r.status_code == 201 and r.data["quantity"] == 2 and r.data["line_total"] == "200.00"
    assert as_user(api, user).get(reverse("api:cart-list")).data["total"] == "200.00"


def test_cart_adding_same_book_merges_quantity(api, user, book):
    as_user(api, user)
    api.post(reverse("api:cart-item-list"), {"book_id": book.pk, "quantity": 2}, format="json")
    api.post(reverse("api:cart-item-list"), {"book_id": book.pk, "quantity": 3}, format="json")
    assert CartItem.objects.get(cart__user=user).quantity == 5


def test_cart_add_over_stock_is_rejected(api, user, make_book):
    book = make_book(stock=2)
    r = as_user(api, user).post(reverse("api:cart-item-list"), {"book_id": book.pk, "quantity": 3}, format="json")
    assert r.status_code == 400 and "quantity" in r.data


def test_cart_item_patch_and_delete(api, user, book):
    as_user(api, user)
    item_id = api.post(reverse("api:cart-item-list"), {"book_id": book.pk}, format="json").data["id"]
    url = reverse("api:cart-item-detail", args=[item_id])
    assert api.patch(url, {"quantity": 4}, format="json").data["quantity"] == 4
    assert api.patch(url, {"quantity": 999}, format="json").status_code == 400
    assert api.delete(url).status_code == 204


def test_cart_items_of_other_user_are_hidden(api, user, other, book):
    item = CartItem.objects.create(cart=Cart.objects.create(user=other), book=book, quantity=1)
    as_user(api, user)
    assert api.get(reverse("api:cart-item-list")).data["count"] == 0
    assert api.delete(reverse("api:cart-item-detail", args=[item.pk])).status_code == 404


def test_cart_clear(api, user, book):
    as_user(api, user).post(reverse("api:cart-item-list"), {"book_id": book.pk}, format="json")
    assert api.post(reverse("api:cart-clear")).status_code == 204
    assert CartItem.objects.filter(cart__user=user).count() == 0


# ------------------------------------------------------------ Orders ---


def test_order_create_from_items_reserves_stock(api, user, book):
    r = as_user(api, user).post(
        reverse("api:order-list"), {"items": [{"book_id": book.pk, "quantity": 2}]}, format="json"
    )
    assert r.status_code == 201
    assert r.data["total"] == "200.00" and r.data["status"] == "pending"
    assert r.data["items"][0]["book"]["title"] == "Kobzar" and r.data["email"] == user.email
    book.refresh_from_db()
    assert book.stock == 8


def test_order_create_from_cart_empties_cart(api, user, book):
    as_user(api, user).post(reverse("api:cart-item-list"), {"book_id": book.pk, "quantity": 3}, format="json")
    r = api.post(reverse("api:order-list"), {}, format="json")
    assert r.status_code == 201 and r.data["total"] == "300.00"
    assert CartItem.objects.filter(cart__user=user).count() == 0


def test_order_with_nothing_is_rejected(api, user):
    r = as_user(api, user).post(reverse("api:order-list"), {}, format="json")
    assert r.status_code == 400 and "items" in r.data and Order.objects.count() == 0


def test_order_not_enough_stock_rolls_back(api, user, make_book):
    book = make_book(stock=1)
    r = as_user(api, user).post(
        reverse("api:order-list"), {"items": [{"book_id": book.pk, "quantity": 5}]}, format="json"
    )
    assert r.status_code == 400
    book.refresh_from_db()
    assert book.stock == 1 and Order.objects.count() == 0


def test_orders_list_shows_only_own(api, user, other, make_order):
    mine = make_order(user=user)
    make_order(user=other)
    r = as_user(api, user).get(reverse("api:order-list"))
    assert [o["id"] for o in r.data["results"]] == [mine.pk]


def test_admin_sees_all_orders(api, admin, user, other, make_order):
    make_order(user=user)
    make_order(user=other)
    assert as_user(api, admin).get(reverse("api:order-list")).data["count"] == 2


def test_order_of_other_user_is_404(api, user, other, make_order):
    order = make_order(user=other)
    assert as_user(api, user).get(reverse("api:order-detail", args=[order.pk])).status_code == 404


def test_order_filter_by_status(api, user, make_order):
    make_order(user=user, status=Order.Status.PAID)
    make_order(user=user, status=Order.Status.PENDING)
    r = as_user(api, user).get(reverse("api:order-list"), {"status": "paid"})
    assert r.data["count"] == 1 and r.data["results"][0]["status"] == "paid"


def test_order_cancel_restocks_book(api, user, book):
    as_user(api, user)
    order_id = api.post(
        reverse("api:order-list"), {"items": [{"book_id": book.pk, "quantity": 4}]}, format="json"
    ).data["id"]
    r = api.post(reverse("api:order-cancel", args=[order_id]))
    assert r.status_code == 200 and r.data["status"] == "cancelled"
    book.refresh_from_db()
    assert book.stock == 10


def test_paid_order_cannot_be_cancelled(api, user, make_order):
    order = make_order(user=user, status=Order.Status.PAID)
    assert as_user(api, user).post(reverse("api:order-cancel", args=[order.pk])).status_code == 400


def test_order_status_change_is_admin_only(api, user, admin, make_order):
    order = make_order(user=user)
    url = reverse("api:order-detail", args=[order.pk])
    assert as_user(api, user).patch(url, {"status": "paid"}, format="json").status_code == 403
    r = as_user(api, admin).patch(url, {"status": "paid"}, format="json")
    assert r.status_code == 200 and r.data["status"] == "paid"


# ------------------------------------------------------- Permissions ---


def _request(method, user):
    request = APIRequestFactory().generic(method, "/")
    request.user = user
    return request


def test_is_owner_or_read_only_allows_safe_methods_for_anyone(user, other, make_order):
    order = make_order(user=other)
    assert IsOwnerOrReadOnly().has_object_permission(_request("GET", user), None, order)


def test_is_owner_or_read_only_allows_owner_to_write(user, make_order):
    order = make_order(user=user)
    assert IsOwnerOrReadOnly().has_object_permission(_request("POST", user), None, order)


def test_is_owner_or_read_only_denies_non_owner_write(user, other, make_order):
    order = make_order(user=other)
    assert not IsOwnerOrReadOnly().has_object_permission(_request("POST", user), None, order)


def test_is_owner_or_read_only_uses_cart_owner_for_items(user, other, book):
    item = CartItem.objects.create(cart=Cart.objects.create(user=user), book=book)
    assert IsOwnerOrReadOnly().has_object_permission(_request("DELETE", user), None, item)
    assert not IsOwnerOrReadOnly().has_object_permission(_request("DELETE", other), None, item)


# -------------------------------------------------------- Throttling ---


def test_anon_throttle_returns_429(api, book):
    with mock.patch.dict(AnonRateThrottle.THROTTLE_RATES, {"anon": "2/min"}):
        codes = [api.get(reverse("api:book-list")).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_user_throttle_returns_429(api, user):
    with mock.patch.dict(UserRateThrottle.THROTTLE_RATES, {"user": "2/min"}):
        as_user(api, user)
        codes = [api.get(reverse("api:cart-list")).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_token_endpoint_has_its_own_throttle(api, user):
    payload = {"username": user.username, "password": "wrong"}
    with mock.patch.dict(TokenObtainThrottle.THROTTLE_RATES, {"token": "2/min"}):
        codes = [api.post(reverse("token_obtain_pair"), payload).status_code for _ in range(3)]
    assert codes == [401, 401, 429]


# -------------------------------------------------------------- CORS ---


def test_cors_allows_configured_origin(api, book):
    r = api.get(reverse("api:book-list"), HTTP_ORIGIN="http://localhost:3000")
    assert r["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_cors_ignores_unknown_origin(api, book):
    r = api.get(reverse("api:book-list"), HTTP_ORIGIN="http://evil.example")
    assert "Access-Control-Allow-Origin" not in r


def test_cors_preflight_request(api):
    r = api.options(
        reverse("api:book-list"),
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )
    assert r.status_code == 200
    assert r["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "POST" in r["Access-Control-Allow-Methods"]


# -------------------------------------------------------------- Docs ---


def test_swagger_docs_page_is_available(api):
    r = api.get("/api/docs/")
    assert r.status_code == 200 and b"swagger" in r.content.lower()


def test_openapi_schema_lists_api_paths(api):
    r = api.get("/api/schema/", {"format": "json"})
    body = r.content.decode()
    assert r.status_code == 200
    for path in ("/api/v1/books/", "/api/v1/categories/", "/api/v1/orders/", "/api/v1/cart/"):
        assert path in body
