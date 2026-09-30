from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import BookForm
from .models import Book, Category

BOOKS_PER_PAGE: int = 4


def _filter_books(queryset: QuerySet[Book], params: QueryDict) -> QuerySet[Book]:
    q = params.get("q", "").strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(author__icontains=q)
            | Q(description__icontains=q)
        )

    category_id = params.get("category", "").strip()
    if category_id.isdigit():
        queryset = queryset.filter(category_id=int(category_id))

    if params.get("in_stock") == "1":
        queryset = queryset.filter(stock__gt=0)

    return queryset


def _preserved_query(params: QueryDict, exclude: tuple[str, ...] = ("page",)) -> str:
    copy = params.copy()
    for key in exclude:
        copy.pop(key, None)
    return copy.urlencode()


def home(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "catalog/home.html",
        {
            "title": "Книжковий магазин",
            "message": "Оберіть книгу в каталозі або додайте нову після входу.",
        },
    )


def book_list_fbv(request: HttpRequest) -> HttpResponse:
    queryset = _filter_books(
        Book.objects.select_related("category").order_by("title"),
        request.GET,
    )
    paginator = Paginator(queryset, BOOKS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "catalog/book_list.html",
        {
            "books": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.paginator.num_pages > 1,
            "view_type": "FBV",
            "categories": Category.objects.order_by("name"),
            "filter_q": request.GET.get("q", ""),
            "filter_category": request.GET.get("category", ""),
            "filter_in_stock": request.GET.get("in_stock", ""),
            "preserved_query": _preserved_query(request.GET),
        },
    )


def book_detail_fbv(request: HttpRequest, pk: int) -> HttpResponse:
    book = get_object_or_404(Book.objects.select_related("category"), pk=pk)
    return render(
        request,
        "catalog/book_detail.html",
        {
            "book": book,
            "view_type": "FBV",
        },
    )


class BookListView(ListView):
    model = Book
    template_name = "catalog/book_list.html"
    context_object_name = "books"
    paginate_by = BOOKS_PER_PAGE

    def get_queryset(self) -> QuerySet[Book]:
        queryset = Book.objects.select_related("category").order_by("title")
        return _filter_books(queryset, self.request.GET)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view_type"] = "CBV"
        context["categories"] = Category.objects.order_by("name")
        context["filter_q"] = self.request.GET.get("q", "")
        context["filter_category"] = self.request.GET.get("category", "")
        context["filter_in_stock"] = self.request.GET.get("in_stock", "")
        context["preserved_query"] = _preserved_query(self.request.GET)
        return context


class BookDetailView(DetailView):
    model = Book
    template_name = "catalog/book_detail.html"
    context_object_name = "book"

    def get_queryset(self) -> QuerySet[Book]:
        return Book.objects.select_related("category")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["view_type"] = "CBV"
        return context


class BookCreateView(LoginRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "catalog/book_form.html"
    success_url = reverse_lazy("catalog:book_list")


class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "catalog/book_form.html"
    context_object_name = "book"

    def get_success_url(self) -> str:
        return str(
            reverse_lazy("catalog:book_detail", kwargs={"pk": self.object.pk})
        )


class BookDeleteView(LoginRequiredMixin, DeleteView):
    model = Book
    template_name = "catalog/book_confirm_delete.html"
    context_object_name = "book"
    success_url = reverse_lazy("catalog:book_list")


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "404.html", status=404)


def server_error(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=500)
