from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone", "is_staff", "is_active")
    search_fields = ("username", "email", "phone")
    fieldsets = UserAdmin.fieldsets + (
        (_("Контакти"), {"fields": ("phone",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_("Контакти"), {"fields": ("phone",)}),
    )
