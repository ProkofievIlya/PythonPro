"""Маршрути додатку catalog (namespace: catalog)."""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    # FBV (навчальні)
    path("books/fbv/", views.book_list_fbv, name="book_list_fbv"),
    path("books/fbv/<int:pk>/", views.book_detail_fbv, name="book_detail_fbv"),
    # CBV — CRUD
    path("books/", views.BookListView.as_view(), name="book_list"),
    path("books/create/", views.BookCreateView.as_view(), name="book_create"),
    path("books/<int:pk>/", views.BookDetailView.as_view(), name="book_detail"),
    path("books/<int:pk>/edit/", views.BookUpdateView.as_view(), name="book_update"),
    path("books/<int:pk>/delete/", views.BookDeleteView.as_view(), name="book_delete"),
]
