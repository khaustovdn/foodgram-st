# backend/recipes/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    BookmarkedRecipe,
    CulinaryRecipe,
    RecipeIngredient,
    ShoppingListRecipe,
)


class RecipeIngredientInline(admin.TabularInline):
    """Inline admin interface for recipe ingredients."""

    model = RecipeIngredient
    extra = 1
    min_num = 1
    verbose_name = _("Ингредиент")
    verbose_name_plural = _("Ингредиенты")


@admin.register(CulinaryRecipe)
class CulinaryRecipeAdmin(admin.ModelAdmin):
    """Administrative interface for recipe management."""

    list_display = ("name", "author", "cooking_time_display")
    search_fields = ("name", "author__username")
    list_filter = ("author",)
    inlines = (RecipeIngredientInline,)
    readonly_fields = ("image_preview",)

    def cooking_time_display(self, obj) -> str:
        """Format cooking time for admin display."""
        return f"{obj.cooking_time} мин"

    cooking_time_display.short_description = _("Время приготовления")

    def image_preview(self, obj) -> str:
        """Generate HTML image preview for admin."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 200px; border-radius: 5px;" />',
                obj.image.url,
            )
        return _("Изображение отсутствует")

    image_preview.short_description = _("Превью изображения")


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    """Administrative interface for recipe-ingredient relationships."""

    list_display = ("recipe", "ingredient", "formatted_amount")
    search_fields = ("recipe__name", "ingredient__name")
    list_filter = ("recipe__author",)

    def formatted_amount(self, obj) -> str:
        """Format amount with measurement unit."""
        return f"{obj.amount} {obj.ingredient.measurement_unit}"

    formatted_amount.short_description = _("Количество")


@admin.register(BookmarkedRecipe)
class BookmarkedRecipeAdmin(admin.ModelAdmin):
    """Administrative interface for bookmarked recipes."""

    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)


@admin.register(ShoppingListRecipe)
class ShoppingListRecipeAdmin(admin.ModelAdmin):
    """Administrative interface for shopping list recipes."""

    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)
