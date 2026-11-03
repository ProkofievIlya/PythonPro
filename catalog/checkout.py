import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from .cart import Cart
from .models import Book, Order, OrderItem

logger = logging.getLogger("bookstore")


def create_order(user, email: str, cart: Cart) -> Order:
    with transaction.atomic():
        order = Order.objects.create(user=user, email=email, total=Decimal("0"))
        total = Decimal("0")
        for row in cart:
            book = Book.objects.select_for_update().get(pk=row["book"].pk)
            quantity = min(row["quantity"], book.stock)
            if quantity < 1:
                continue
            OrderItem.objects.create(
                order=order,
                book=book,
                price=book.price,
                quantity=quantity,
            )
            book.stock -= quantity
            book.save(update_fields=["stock"])
            total += book.price * quantity
        if total <= 0:
            raise ValueError("Кошик порожній")
        order.total = total
        order.save(update_fields=["total"])
    return order


def start_checkout(request: HttpRequest, order: Order) -> str:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    line_items = []
    for item in order.items.select_related("book"):
        line_items.append(
            {
                "price_data": {
                    "currency": "uah",
                    "unit_amount": int(item.price * 100),
                    "product_data": {"name": item.book.localized_title},
                },
                "quantity": item.quantity,
            }
        )
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=order.email,
        client_reference_id=str(order.pk),
        metadata={"order_id": str(order.pk)},
        line_items=line_items,
        success_url=request.build_absolute_uri("/checkout/success/")
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri("/checkout/cancel/"),
    )
    order.stripe_session_id = session.id
    order.save(update_fields=["stripe_session_id"])
    return session.url


def is_session_paid(session_id: str) -> bool:
    """Питаємо Stripe, чи справді сесію оплачено (не віримо параметру з URL)."""
    if not session_id or not settings.STRIPE_SECRET_KEY:
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        logger.warning("Stripe: не вдалося отримати сесію %s", session_id)
        return False
    return getattr(session, "payment_status", None) == "paid"


def mark_order_paid(session_id: str) -> Order | None:
    """Переводить замовлення PENDING -> PAID і після коміту надсилає лист."""
    order = Order.objects.filter(stripe_session_id=session_id).first()
    if order is None:
        return None
    if order.status != Order.Status.PENDING:
        if order.status == Order.Status.CANCELLED:
            logger.warning("Оплата скасованого замовлення #%s (%s)", order.pk, session_id)
        return order
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != Order.Status.PENDING:
            return order
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])
        order_id = order.pk
        transaction.on_commit(lambda: send_order_email(order_id))
    return order


def cancel_order_by_session(session_id: str) -> Order | None:
    order = Order.objects.filter(stripe_session_id=session_id).first()
    if order is not None:
        cancel_order(order)
        order.refresh_from_db()
    return order


def cancel_stale_orders(older_than: timedelta = timedelta(hours=24)) -> int:
    """Скасовує неоплачені замовлення, старші за older_than; повертає їх кількість."""
    cutoff = timezone.now() - older_than
    stale = list(Order.objects.filter(status=Order.Status.PENDING, created_at__lt=cutoff))
    for order in stale:
        cancel_order(order)
    return len(stale)


def cancel_order(order: Order) -> None:
    if order.status != Order.Status.PENDING:
        return
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != Order.Status.PENDING:
            return
        for item in order.items.select_related("book"):
            book = Book.objects.select_for_update().get(pk=item.book_id)
            book.stock += item.quantity
            book.save(update_fields=["stock"])
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])


def send_order_email(order_id: int) -> None:
    order = Order.objects.prefetch_related("items__book").get(pk=order_id)
    if not order.email:
        return
    lines = [
        f"{item.book.localized_title} × {item.quantity} — {item.line_total} ₴"
        for item in order.items.all()
    ]
    lines.append(_("Разом: %(total)s ₴") % {"total": order.total})
    send_mail(
        subject=_("Замовлення #%(pk)s") % {"pk": order.pk},
        message="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=False,
    )

