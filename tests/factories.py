"""factory-boy фабрики для моделей проєкту."""

from decimal import Decimal

import factory
from django.contrib.auth.hashers import make_password

DEFAULT_PASSWORD = "S3cret-pass!"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "accounts.CustomUser"
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.LazyFunction(lambda: make_password(DEFAULT_PASSWORD))
    phone = ""


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.Category"

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.Book"

    title = factory.Sequence(lambda n: f"Book {n}")
    author = factory.Faker("name")
    price = Decimal("100.00")
    description = factory.Faker("sentence")
    stock = 10
    category = factory.SubFactory(CategoryFactory)


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.Order"

    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda obj: obj.user.email)
    total = Decimal("0.00")


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "catalog.OrderItem"

    order = factory.SubFactory(OrderFactory)
    book = factory.SubFactory(BookFactory)
    price = factory.LazyAttribute(lambda obj: obj.book.price)
    quantity = 1
