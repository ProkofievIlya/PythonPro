"""Асинхронні JSON-в'ю з async ORM (``aget``, ``acount``, ``aaggregate``, ``async for``)."""

import asyncio
from typing import Any

from django.db.models import Avg, Count, Sum
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .models import Book, Category, Order
from .views import _filter_books, ordered_by_title

SEARCH_LIMIT: int = 20
ORDERS_LIMIT: int = 50
_JSON_PARAMS = {"ensure_ascii": False}


def _json(data: dict[str, Any], status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status, json_dumps_params=_JSON_PARAMS)


def _book_payload(book: Book) -> dict[str, Any]:
    return {
        "id": book.pk,
        "title": book.localized_title,
        "author": book.localized_author,
        "price": str(book.price),
        "stock": book.stock,
        "in_stock": book.in_stock,
    }


@require_GET
async def stats_api(request: HttpRequest) -> JsonResponse:
    """Зведена статистика каталогу: чотири запити виконуються через gather."""
    total, in_stock, categories, aggregates = await asyncio.gather(
        Book.objects.acount(),
        Book.objects.filter(stock__gt=0).acount(),
        Category.objects.acount(),
        Book.objects.aaggregate(avg_price=Avg("price"), total_stock=Sum("stock")),
    )
    avg_price = aggregates["avg_price"]
    return _json(
        {
            "books_total": total,
            "books_in_stock": in_stock,
            "categories_total": categories,
            "total_stock": aggregates["total_stock"] or 0,
            "avg_price": round(float(avg_price), 2) if avg_price is not None else 0,
        }
    )


@require_GET
async def search_api(request: HttpRequest) -> JsonResponse:
    """Пошук книг (ті самі фільтри ?q=, ?category=, ?in_stock=1, що й у каталозі)."""
    queryset = _filter_books(
        ordered_by_title(Book.objects.select_related("category")),
        request.GET,
    )
    count = await queryset.acount()
    results = []
    async for book in queryset[:SEARCH_LIMIT]:
        item = _book_payload(book)
        item["category"] = book.category.localized_name
        results.append(item)
    return _json({"count": count, "results": results})


@require_GET
async def category_api(request: HttpRequest, slug: str) -> JsonResponse:
    """Категорія за slug разом з її книгами."""
    try:
        category = await Category.objects.aget(slug=slug)
    except Category.DoesNotExist:
        return _json({"error": _("Категорію не знайдено.")}, status=404)
    books = [_book_payload(book) async for book in ordered_by_title(category.books.all())]
    return _json(
        {
            "id": category.pk,
            "name": category.localized_name,
            "slug": category.slug,
            "books": books,
        }
    )


@require_GET
async def my_orders_api(request: HttpRequest) -> JsonResponse:
    """Замовлення поточного користувача (async-варіант request.user)."""
    user = await request.auser()
    if not user.is_authenticated:
        return _json({"error": _("Потрібна авторизація.")}, status=401)
    orders = (
        Order.objects.filter(user=user)
        .annotate(items_count=Count("items"))
        .order_by("-created_at")[:ORDERS_LIMIT]
    )
    results = [
        {
            "id": order.pk,
            "status": order.status,
            "status_display": str(order.get_status_display()),
            "total": str(order.total),
            "items_count": order.items_count,
            "created_at": order.created_at.isoformat(),
        }
        async for order in orders
    ]
    return _json({"count": len(results), "results": results})
