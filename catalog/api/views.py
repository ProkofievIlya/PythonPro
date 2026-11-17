from django.db import transaction
from django.db.models import Count, F
from django.db.models.deletion import ProtectedError
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from catalog.models import Book, Cart, CartItem, Category, Order

from .filters import BookFilter, CategoryFilter, OrderFilter
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    BookSerializer,
    CartItemSerializer,
    CartSerializer,
    CategoryDetailSerializer,
    CategorySerializer,
    OrderAdminSerializer,
    OrderSerializer,
)
from .throttles import TokenObtainThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [TokenObtainThrottle]


def _is_schema_gen(view) -> bool:
    return getattr(view, "swagger_fake_view", False)


class AdminWriteMixin:
    """Читати може будь-хто, створювати/змінювати/видаляти - лише адміністратор."""

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Cannot delete: referenced by existing orders."},
                status=status.HTTP_409_CONFLICT,
            )


class CategoryViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = Category.objects.annotate(books_count=Count("books")).order_by("name")
    serializer_class = CategorySerializer
    filterset_class = CategoryFilter
    search_fields = ["name", "name_en"]
    ordering_fields = ["name", "books_count"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related("books") if self.action == "retrieve" else qs

    def get_serializer_class(self):
        return CategoryDetailSerializer if self.action == "retrieve" else CategorySerializer


class BookViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = Book.objects.select_related("category").order_by("title", "id")
    serializer_class = BookSerializer
    filterset_class = BookFilter
    search_fields = ["title", "author", "title_en", "author_en", "description"]
    ordering_fields = ["price", "title", "created_at", "stock"]


class OrderViewSet(viewsets.ModelViewSet):
    """Користувач бачить і створює свої замовлення; змінює/видаляє лише адміністратор."""

    queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "total"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if _is_schema_gen(self):
            return Order.objects.none()
        qs = Order.objects.select_related("user").prefetch_related("items__book")
        user = self.request.user
        return qs if user.is_staff else qs.filter(user=user)

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return OrderAdminSerializer
        return OrderSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    @extend_schema(request=None, responses=OrderSerializer)
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsOwnerOrReadOnly],
    )
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.Status.PENDING:
            return Response(
                {"detail": "Only pending orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            for item in order.items.all():
                Book.objects.filter(pk=item.book_id).update(stock=F("stock") + item.quantity)
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status"])
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)


class CartViewSet(viewsets.GenericViewSet):
    """Кошик поточного користувача: GET /cart/ і POST /cart/clear/."""

    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        if _is_schema_gen(self):
            return Cart.objects.none()
        return Cart.objects.filter(user=self.request.user).prefetch_related("items__book__category")

    @extend_schema(responses=CartSerializer)
    def list(self, request):
        Cart.objects.get_or_create(user=request.user)
        return Response(self.get_serializer(self.get_queryset().get()).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=False, methods=["post"])
    def clear(self, request):
        CartItem.objects.filter(cart__user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "quantity"]

    def get_queryset(self):
        if _is_schema_gen(self):
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__user=self.request.user).select_related("book__category")
