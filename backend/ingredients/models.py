# backend/ingredients/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _


class CulinaryIngredient(models.Model):
    """Represents a culinary ingredient with measurement information."""

    class Meta:
        verbose_name = _("Ингредиент")
        verbose_name_plural = _("Ингредиенты")
        ordering = ("name",)

    name = models.CharField(
        verbose_name=_("Название ингредиента"),
        max_length=128,
    )

    measurement_unit = models.CharField(
        verbose_name=_("Единица измерения"),
        max_length=32,
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.measurement_unit})"

    def natural_key(self):
        """Return natural key for serialization."""
        return (self.name,)
