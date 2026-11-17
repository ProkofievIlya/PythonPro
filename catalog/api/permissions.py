from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Читати може будь-хто з доступом до об'єкта, змінювати - лише його власник.

    Власник визначається за полем ``user`` об'єкта або за ``cart.user`` (позиція кошика).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "user", None)
        if owner is None and hasattr(obj, "cart"):
            owner = obj.cart.user
        return owner is not None and owner == request.user
