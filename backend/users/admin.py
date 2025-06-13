# backend/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import ChefSubscription, CulinaryUser


class CulinaryUserAdmin(UserAdmin):
    """Custom administrative interface for CulinaryUser model."""

    list_display = ("email", "username", "first_name", "last_name")
    search_fields = ("email", "username")
    list_filter = ("is_staff", "is_superuser")
    ordering = ("email",)
    fieldsets = (
        (
            _("Учетные данные"),
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            _("Персональная информация"),
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "avatar",
                )
            },
        ),
        (
            _("Статусы и разрешения"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(ChefSubscription)
class ChefSubscriptionAdmin(admin.ModelAdmin):
    """Administrative interface for chef subscriptions."""

    list_display = ("follower", "author")
    search_fields = (
        "follower__username",
        "author__username",
    )
    list_filter = ("follower", "author")


admin.site.register(CulinaryUser, CulinaryUserAdmin)
