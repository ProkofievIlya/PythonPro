from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("catalog.urls", "catalog"), namespace="catalog")),
]

handler404 = "catalog.views.page_not_found"
handler500 = "catalog.views.server_error"
