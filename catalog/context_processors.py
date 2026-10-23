def cart_count(request):
    raw = {}
    if hasattr(request, "session"):
        raw = request.session.get("cart") or {}
    total = 0
    for quantity in raw.values():
        try:
            total += int(quantity)
        except (TypeError, ValueError):
            continue
    return {"cart_count": total}
