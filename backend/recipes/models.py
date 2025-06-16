# backend/recipes/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _

from ingredients.models import CulinaryIngredient
from users.models import CulinaryUser


class CulinaryRecipe(models.Model):
    """Represents a culinary recipe with preparation details."""

    class Meta:
        ordering = ("name",)
        verbose_name = _("Рецепт")
        verbose_name_plural = _("Рецепты")

    name = models.CharField(verbose_name=_("Название рецепта"), max_length=256)
    text = models.TextField(
        verbose_name=_("Описание рецепта"),
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name=_("Время приготовления (минуты)"),
    )
    image = models.ImageField(
        verbose_name=_("Изображение блюда"), upload_to="image/recipes/%Y/%m/%d/"
    )
    ingredients = models.ManyToManyField(
        CulinaryIngredient,
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name=_("Ингредиенты рецепта"),
    )
    author = models.ForeignKey(
        CulinaryUser,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name=_("Автор рецепта"),
    )

    def __str__(self) -> str:
        return self.name


class RecipeIngredient(models.Model):
    """Links ingredients to recipes with quantity information."""

    class Meta:
        ordering = ("recipe", "ingredient")
        verbose_name = _("Ингредиент рецепта")
        verbose_name_plural = _("Ингредиенты рецептов")

    recipe = models.ForeignKey(
        CulinaryRecipe,
        on_delete=models.CASCADE,
        related_name="recipes_ingredients",
        verbose_name=_("Рецепт"),
    )
    ingredient = models.ForeignKey(
        CulinaryIngredient,
        on_delete=models.CASCADE,
        related_name="used_in_recipes",
        verbose_name=_("Ингредиент"),
    )
    amount = models.PositiveIntegerField(
        verbose_name=_("Количество"),
    )

    def __str__(self) -> str:
        return f"{self.ingredient} - {self.amount} {self.ingredient.measurement_unit}"


class UserRecipeInteraction(models.Model):
    """Abstract model for user-recipe relationships."""

    class Meta:
        abstract = True
        ordering = ("user", "recipe")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="%(app_label)s_%(class)s_unique_relation",
            )
        ]

    user = models.ForeignKey(
        CulinaryUser, on_delete=models.CASCADE, verbose_name=_("Пользователь")
    )
    recipe = models.ForeignKey(
        CulinaryRecipe, on_delete=models.CASCADE, verbose_name=_("Рецепт")
    )

    def __str__(self) -> str:
        return f"{self.user} - {self.recipe}"


class BookmarkedRecipe(UserRecipeInteraction):
    """Represents a recipe bookmarked by a user."""

    class Meta(UserRecipeInteraction.Meta):
        verbose_name = _("Избранный рецепт")
        verbose_name_plural = _("Избранные рецепты")

    recipe = models.ForeignKey(
        CulinaryRecipe,
        on_delete=models.CASCADE,
        verbose_name=_("Рецепт"),
        related_name="bookmarked",
    )


class ShoppingListRecipe(UserRecipeInteraction):
    """Represents a recipe added to user's shopping list."""

    class Meta(UserRecipeInteraction.Meta):
        verbose_name = _("Рецепт в корзине")
        verbose_name_plural = _("Рецепты в корзинах")

    recipe = models.ForeignKey(
        CulinaryRecipe,
        on_delete=models.CASCADE,
        verbose_name=_("Рецепт"),
        related_name="shoppinglist",
    )
