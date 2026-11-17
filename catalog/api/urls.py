from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("books", views.BookViewSet, basename="book")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("orders", views.OrderViewSet, basename="order")
router.register("cart", views.CartViewSet, basename="cart")
router.register("cart-items", views.CartItemViewSet, basename="cart-item")

urlpatterns = router.urls
