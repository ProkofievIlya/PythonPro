from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Book, Category, Order, OrderItem


class BookInline(admin.TabularInline):
    model = Book
    extra = 1
    fields = ("title", "title_en", "author", "price", "stock")
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "slug", "book_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "name_en", "slug")
    inlines = (BookInline,)

    @admin.display(description=_("Кількість книг"))
    def book_count(self, obj: Category) -> int:
        return obj.books.count()


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "created_at", "price", "stock")
    list_filter = ("category", "created_at")
    search_fields = ("title", "title_en", "author", "author_en", "description")
    list_editable = ("price", "stock")
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("title", "author", "category")}),
        (_("Деталі"), {"fields": ("price", "stock", "description", "cover")}),
        (_("Англійською"), {"fields": ("title_en", "author_en", "description_en")}),
        (_("Системне"), {"fields": ("created_at",)}),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("book", "price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "email", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("email", "user__username", "stripe_session_id")
    readonly_fields = ("created_at", "stripe_session_id", "total")
    inlines = (OrderItemInline,)
