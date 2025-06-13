# backend/ingredients/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import CulinaryIngredient


@admin.register(CulinaryIngredient)
class CulinaryIngredientAdmin(admin.ModelAdmin):
    """Administrative interface for culinary ingredients."""

    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)
    ordering = ("name",)
