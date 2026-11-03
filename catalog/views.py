from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet, Value
from django.db.models.functions import Coalesce, NullIf
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

import logging

import stripe

from .cart import Cart
from .checkout import (
    cancel_order,
    cancel_order_by_session,
    create_order,
    is_session_paid,
    mark_order_paid,
    start_checkout,
)
from .forms import BookForm, CheckoutForm
from .models import Book, Category, Order

BOOKS_PER_PAGE: int = 4

logger = logging.getLogger("bookstore")


def _filter_books(queryset: QuerySet[Book], params: QueryDict) -> QuerySet[Book]:
    q = params.get("q", "").strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(author__icontains=q)
            | Q(description__icontains=q)
            | Q(title_en__icontains=q)
            | Q(author_en__icontains=q)
            | Q(description_en__icontains=q)
        )

    category_id = params.get("category", "").strip()
    if category_id.isdigit():
        queryset = queryset.filter(category_id=int(category_id))

    if params.get("in_stock") == "1":
        queryset = queryset.filter(stock__gt=0)

    return queryset


def ordered_by_title(queryset: QuerySet[Book]) -> QuerySet[Book]:
    """Сортування за назвою мовою інтерфейсу (в EN - за title_en, якщо заповнена)."""
    if (get_language() or "").startswith("en"):
        return queryset.annotate(
            sort_title=Coalesce(NullIf("title_en", Value("")), "title")
        ).order_by("sort_title", "pk")
    return queryset.order_by("title", "pk")


def _preserved_query(params: QueryDict, exclude: tuple[str, ...] = ("page",)) -> str:
    copy = params.copy()
    for key in exclude:
        copy.pop(key, None)
    return copy.urlencode()


def home(request: HttpRequest) -> HttpResponse:
    featured = (
        Book.objects.filter(stock__gt=0)
        .select_related("category")
        .order_by("-created_at")[:4]
    )
    return render(
        request,
        "catalog/home.html",
        {
            "title": _("Книги, які залишаються з вами"),
            "message": _(
                "Художні, наукові й дитячі видання. Оберіть книгу і покладіть її в кошик."
            ),
            "featured": featured,
        },
    )


def book_list_fbv(request: HttpRequest) -> HttpResponse:
    queryset = _filter_books(
        ordered_by_title(Book.objects.select_related("category")),
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
        queryset = ordered_by_title(Book.objects.select_related("category"))
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


class BookCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "catalog.add_book"
    model = Book
    form_class = BookForm
    template_name = "catalog/book_form.html"
    success_url = reverse_lazy("catalog:book_list")


class BookUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "catalog.change_book"
    model = Book
    form_class = BookForm
    template_name = "catalog/book_form.html"
    context_object_name = "book"

    def get_success_url(self) -> str:
        return str(
            reverse_lazy("catalog:book_detail", kwargs={"pk": self.object.pk})
        )


class BookDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "catalog.delete_book"
    model = Book
    template_name = "catalog/book_confirm_delete.html"
    context_object_name = "book"
    success_url = reverse_lazy("catalog:book_list")


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "404.html", status=404)


def server_error(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=500)


@require_POST
def cart_add(request: HttpRequest, pk: int) -> HttpResponse:
    book = get_object_or_404(Book, pk=pk)
    Cart(request).add(book)
    return redirect("catalog:cart_detail")


@require_POST
def cart_decrease(request: HttpRequest, pk: int) -> HttpResponse:
    book = get_object_or_404(Book, pk=pk)
    Cart(request).decrease(book)
    return redirect("catalog:cart_detail")


@require_POST
def cart_remove(request: HttpRequest, pk: int) -> HttpResponse:
    book = get_object_or_404(Book, pk=pk)
    Cart(request).remove(book)
    return redirect("catalog:cart_detail")


@require_POST
def cart_clear(request: HttpRequest) -> HttpResponse:
    Cart(request).clear()
    return redirect("catalog:cart_detail")


def cart_detail(request: HttpRequest) -> HttpResponse:
    cart = Cart(request)
    return render(
        request,
        "catalog/cart.html",
        {
            "cart": cart,
            "email": request.user.email if request.user.is_authenticated else "",
        },
    )


@login_required
@require_POST
def checkout(request: HttpRequest) -> HttpResponse:
    cart = Cart(request)
    if len(cart) == 0:
        messages.error(request, _("Кошик порожній."))
        return redirect("catalog:cart_detail")
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors["email"][0])
        return redirect("catalog:cart_detail")
    email = form.cleaned_data["email"]
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, _("Оплата Stripe ще не налаштована."))
        return redirect("catalog:cart_detail")
    order = None
    try:
        order = create_order(request.user, email, cart)
        url = start_checkout(request, order)
    except Exception:
        if order is not None:
            cancel_order(order)
        messages.error(request, _("Не вдалося створити оплату. Спробуйте ще раз."))
        return redirect("catalog:cart_detail")
    request.session["pending_order_id"] = order.pk
    cart.clear()
    return redirect(url)


@login_required
def checkout_success(request: HttpRequest) -> HttpResponse:
    """Повернення зі Stripe. Оплату перевіряємо у Stripe, а не за параметром URL."""
    session_id = request.GET.get("session_id", "")
    order = None
    if session_id:
        order = Order.objects.filter(
            stripe_session_id=session_id, user=request.user
        ).first()
    if order is not None and order.status == Order.Status.PENDING:
        if is_session_paid(session_id):
            order = mark_order_paid(session_id)
    paid_order = order if order is not None and order.status == Order.Status.PAID else None
    if paid_order is not None:
        request.session.pop("pending_order_id", None)
    return render(request, "catalog/checkout_success.html", {"order": paid_order})


@login_required
def checkout_cancel(request: HttpRequest) -> HttpResponse:
    order_id = request.session.pop("pending_order_id", None)
    if order_id:
        order = Order.objects.filter(pk=order_id, user=request.user).first()
        if order:
            cancel_order(order)
    messages.info(request, _("Оплату скасовано."))
    return redirect("catalog:cart_detail")


PAID_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
FAILED_EVENTS = {"checkout.session.expired", "checkout.session.async_payment_failed"}


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> JsonResponse:
    """Події Stripe приймаємо лише з перевіреним підписом."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook відхилено: STRIPE_WEBHOOK_SECRET не задано")
        return JsonResponse({"error": "webhook secret is not configured"}, status=400)
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            request.body, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({"error": "invalid payload"}, status=400)
    event_type = event["type"]
    session = event["data"]["object"]
    session_id = session.get("id", "")
    if event_type in PAID_EVENTS and session.get("payment_status") == "paid":
        mark_order_paid(session_id)
    elif event_type in FAILED_EVENTS:
        cancel_order_by_session(session_id)
    return JsonResponse({"status": "ok"})
