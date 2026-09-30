from django.contrib import admin

from .models import Book, Category


class BookInline(admin.TabularInline):
    model = Book
    extra = 1
    fields = ("title", "author", "price", "stock")
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "book_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    inlines = (BookInline,)

    @admin.display(description="Кількість книг")
    def book_count(self, obj: Category) -> int:
        return obj.books.count()


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "created_at", "price", "stock")
    list_filter = ("category", "created_at")
    search_fields = ("title", "author", "description")
    list_editable = ("price", "stock")
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("title", "author", "category")}),
        ("Деталі", {"fields": ("price", "stock", "description")}),
        ("Системне", {"fields": ("created_at",)}),
    )
