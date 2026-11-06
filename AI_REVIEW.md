# AI Code Review

Для ревʼю обрано три найскладніші в'ю проєкту: `checkout`, `checkout_success`, `stripe_webhook` (`catalog/views.py`). Ревʼю виконано за допомогою AI-асистента з промптом із `AI_PROMPTS.md` (розділ 1). Нижче для кожного в'ю: оригінальний код, рекомендації AI (з рішенням: застосовано чи відхилено) та фінальний код.

> Нову поведінку (логування збою checkout, вебхук без `id`, вебхук для невідомого замовлення) покрито в `tests/unit/test_review_fixes.py`. Рефакторинг `checkout_success` перевіряється наявними тестами `tests/unit/test_views.py` та `tests/integration/test_user_flows.py`, які не змінювались.

## 1. `checkout` — Оформлення замовлення

### Оригінальний код

```python
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
```

### Рекомендації AI

- **Валідно, застосовано:** `except Exception` ковтає будь-яку помилку без сліду в логах, тому збої Stripe неможливо розслідувати. Додано `logger.exception(...)` з номером замовлення.
- **Відхилено:** звузити `except Exception` до `(ValueError, stripe.StripeError)`. Це змінило б поведінку: будь-яка несподівана помилка (БД, мережа) не скасувала б замовлення, а товар лишився б зарезервованим. Широкий `except` тут навмисний, бо після нього завжди виконується `cancel_order`.
- **Відхилено:** показувати окреме повідомлення «товару немає» для `ValueError`. Це потребує нових перекладів і зміни наявних тестів, а на безпеку не впливає.

### Фінальний код

```python
@login_required
@require_POST
def checkout(request: HttpRequest) -> HttpResponse:
    """Оформлення замовлення: резервує товар, створює сесію Stripe і перенаправляє на оплату.

    Помилка Stripe скасовує замовлення й повертає товар на склад."""
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
        logger.exception("Checkout: не вдалося створити оплату (замовлення %s)", getattr(order, "pk", None))
        if order is not None:
            cancel_order(order)
        messages.error(request, _("Не вдалося створити оплату. Спробуйте ще раз."))
        return redirect("catalog:cart_detail")
    request.session["pending_order_id"] = order.pk
    cart.clear()
    return redirect(url)
```

## 2. `checkout_success` — Повернення зі Stripe

### Оригінальний код

```python
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
```

### Рекомендації AI

- **Валідно, застосовано:** три вкладені умови зведено в одну, а `mark_order_paid(...)` може повернути `None` при гонці з вебхуком, тому додано `or order`, щоб не втратити змінну `order`.
- **Відхилено:** довіряти параметру `session_id` без запиту до Stripe. Поточна логіка (перевірка через `is_session_paid` і фільтр `user=request.user`) правильна: параметр з URL можна підробити.

### Фінальний код

```python
@login_required
def checkout_success(request: HttpRequest) -> HttpResponse:
    """Повернення зі Stripe. Оплату перевіряємо у Stripe, а не за параметром URL."""
    session_id = request.GET.get("session_id", "")
    order = None
    if session_id:
        order = Order.objects.filter(
            stripe_session_id=session_id, user=request.user
        ).first()
    if (
        order is not None
        and order.status == Order.Status.PENDING
        and is_session_paid(session_id)
    ):
        order = mark_order_paid(session_id) or order
    paid_order = order if order is not None and order.status == Order.Status.PAID else None
    if paid_order is not None:
        request.session.pop("pending_order_id", None)
    return render(request, "catalog/checkout_success.html", {"order": paid_order})
```

## 3. `stripe_webhook` — Вебхук Stripe

### Оригінальний код

```python
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
```

### Рекомендації AI

- **Валідно, застосовано:** подія без `id` сесії тепер ігнорується з попередженням у лозі (`{"status": "ignored"}`), а не передається у `mark_order_paid("")`.
- **Валідно, застосовано:** якщо замовлення для сесії не знайдено, пишемо `logger.warning`. Раніше такі події зникали мовчки. Для подій інших типів одразу повертаємо `ok`.
- **Відхилено:** звіряти `amount_total` події з `order.total`. Ідея слушна, але тестові події (`tests/conftest.py`) не містять суми, тому її варто додавати разом з оновленням фікстур окремим уроком.

### Фінальний код

```python
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
    if not session_id:
        logger.warning("Stripe webhook %s без id сесії - пропущено", event_type)
        return JsonResponse({"status": "ignored"})
    order = None
    if event_type in PAID_EVENTS and session.get("payment_status") == "paid":
        order = mark_order_paid(session_id)
    elif event_type in FAILED_EVENTS:
        order = cancel_order_by_session(session_id)
    else:
        return JsonResponse({"status": "ok"})
    if order is None:
        logger.warning("Stripe webhook %s: замовлення для сесії %s не знайдено", event_type, session_id)
    return JsonResponse({"status": "ok"})
```
