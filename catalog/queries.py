from decimal import Decimal

from django.db.models import Avg, Count, Q, QuerySet, Sum

from .models import Book, Category


def books_in_stock() -> QuerySet[Book]:
    return Book.objects.filter(stock__gt=0)


def books_by_price_range(
    min_price: Decimal, max_price: Decimal
) -> QuerySet[Book]:
    return Book.objects.filter(price__gte=min_price, price__lte=max_price)


def search_books(text: str) -> QuerySet[Book]:
    return Book.objects.filter(
        Q(title__icontains=text)
        | Q(author__icontains=text)
        | Q(description__icontains=text)
    )


def available_or_cheap_books(max_price: Decimal) -> QuerySet[Book]:
    return Book.objects.filter(Q(stock__gt=0) | Q(price__lte=max_price)).distinct()


def categories_with_stats() -> QuerySet[Category]:
    return Category.objects.annotate(
        book_count=Count("books"),
        total_stock=Sum("books__stock"),
        avg_price=Avg("books__price"),
    )


def top_categories_by_books(limit: int = 5) -> QuerySet[Category]:
    return (
        Category.objects.annotate(book_count=Count("books"))
        .filter(book_count__gt=0)
        .order_by("-book_count")[:limit]
    )


def books_in_category_slug(slug: str) -> QuerySet[Book]:
    return Book.objects.filter(category__slug=slug).select_related("category")
