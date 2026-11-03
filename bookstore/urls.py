from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("allauth.urls")),
    path("", include(("catalog.urls", "catalog"), namespace="catalog")),
]

# Завантажені обкладинки (працює лише при DEBUG=True; у продакшені їх віддає веб-сервер).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns = [
        path("__debug__/", include("debug_toolbar.urls")),
    ] + urlpatterns

handler403 = "accounts.views.permission_denied"
handler404 = "catalog.views.page_not_found"
handler500 = "catalog.views.server_error"
