from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from catalog.models import Book, Cart, CartItem, Category, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "name_en", "slug", "books_count"]


class BookShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "price", "stock"]


class CategoryDetailSerializer(CategorySerializer):
    """Категорія з вкладеним списком книг."""

    books = BookShortSerializer(many=True, read_only=True)

    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ["books"]


class BookSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Book
        fields = [
            "id", "title", "author", "price", "description", "stock", "in_stock",
            "category", "category_id", "title_en", "author_en", "description_en",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value


class CartItemSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source="book", write_only=True
    )
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "book", "book_id", "quantity", "line_total"]
        extra_kwargs = {"quantity": {"min_value": 1}}

    def validate(self, attrs):
        book = attrs.get("book") or (self.instance.book if self.instance else None)
        if self.instance is None and book is None:
            raise serializers.ValidationError({"book_id": "This field is required."})
        quantity = attrs.get("quantity", self.instance.quantity if self.instance else 1)
        if quantity > book.stock:
            raise serializers.ValidationError(
                {"quantity": f"Only {book.stock} in stock."}
            )
        return attrs

    def create(self, validated_data):
        cart, _ = Cart.objects.get_or_create(user=self.context["request"].user)
        book = validated_data["book"]
        quantity = validated_data.get("quantity", 1)
        item, created = CartItem.objects.get_or_create(
            cart=cart, book=book, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, book.stock)
            item.save(update_fields=["quantity"])
        return item

    def update(self, instance, validated_data):
        validated_data.pop("book", None)  # книгу в позиції змінювати не можна
        return super().update(instance, validated_data)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "updated_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    book = BookShortSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source="book", write_only=True
    )
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "book", "book_id", "price", "quantity", "line_total"]
        read_only_fields = ["price"]
        extra_kwargs = {"quantity": {"min_value": 1}}


class OrderSerializer(serializers.ModelSerializer):
    """Замовлення з вкладеними позиціями.

    Створення: ``items`` (список ``{book_id, quantity}``) або, якщо його не передано,
    вміст кошика користувача. Залишки книг резервуються одразу.
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, required=False)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "email", "status", "status_display", "total", "items", "created_at"]
        read_only_fields = ["status", "total", "created_at"]
        extra_kwargs = {"email": {"required": False}}

    def create(self, validated_data):
        user = self.context["request"].user
        items = validated_data.pop("items", None)
        email = validated_data.get("email") or user.email
        cart = None
        if items:
            wanted: dict[int, int] = {}
            for row in items:
                wanted[row["book"].pk] = wanted.get(row["book"].pk, 0) + row["quantity"]
        else:
            cart = Cart.objects.filter(user=user).first()
            wanted = {i.book_id: i.quantity for i in cart.items.all()} if cart else {}
        if not wanted:
            raise serializers.ValidationError({"items": "No items given and the cart is empty."})

        with transaction.atomic():
            order = Order.objects.create(user=user, email=email, total=Decimal("0"))
            total = Decimal("0")
            for book_id, quantity in wanted.items():
                book = Book.objects.select_for_update().get(pk=book_id)
                if quantity > book.stock:
                    raise serializers.ValidationError(
                        {"items": f"Not enough stock for '{book.title}': {book.stock} left."}
                    )
                OrderItem.objects.create(order=order, book=book, price=book.price, quantity=quantity)
                book.stock -= quantity
                book.save(update_fields=["stock"])
                total += book.price * quantity
            order.total = total
            order.save(update_fields=["total"])
            if cart is not None:
                cart.items.all().delete()
        return order


class OrderAdminSerializer(OrderSerializer):
    """Для адміністратора: можна змінювати статус (і email); позиції лише для читання."""

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        read_only_fields = ["total", "created_at"]
