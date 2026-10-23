from decimal import Decimal

from django.http import HttpRequest

from .models import Book

SESSION_KEY = "cart"


class Cart:
    def __init__(self, request: HttpRequest) -> None:
        self.session = request.session
        cart = self.session.get(SESSION_KEY)
        if cart is None:
            cart = self.session[SESSION_KEY] = {}
        self.cart = cart

    def add(self, book: Book, quantity: int = 1) -> None:
        if quantity < 1 or book.stock < 1:
            return
        key = str(book.pk)
        current = int(self.cart.get(key, 0))
        self.cart[key] = min(current + quantity, book.stock)
        self.session.modified = True

    def decrease(self, book: Book, quantity: int = 1) -> None:
        key = str(book.pk)
        if key not in self.cart or quantity < 1:
            return
        current = int(self.cart[key]) - quantity
        if current < 1:
            del self.cart[key]
        else:
            self.cart[key] = current
        self.session.modified = True

    def remove(self, book: Book) -> None:
        key = str(book.pk)
        if key in self.cart:
            del self.cart[key]
            self.session.modified = True

    def clear(self) -> None:
        self.session[SESSION_KEY] = {}
        self.cart = self.session[SESSION_KEY]
        self.session.modified = True

    def __iter__(self):
        books = Book.objects.filter(pk__in=self.cart.keys())
        found = {str(book.pk): book for book in books}
        for book_id, quantity in list(self.cart.items()):
            book = found.get(str(book_id))
            if book is None:
                continue
            qty = int(quantity)
            yield {
                "book": book,
                "quantity": qty,
                "total": book.price * qty,
            }

    def __len__(self) -> int:
        return sum(int(quantity) for quantity in self.cart.values())

    @property
    def total(self) -> Decimal:
        return sum((row["total"] for row in self), Decimal("0"))
