from django.utils.translation import gettext_lazy as _
from django.db import models


class Ingredient(models.Model):
    name = models.CharField(
        _('Название ингредиента'),
        max_length=64,
        blank=False,
        unique=True,
    )
    unit_of_measurement = models.CharField(
        _('Единица измерения'),
        max_length=32,
        blank=False,
    )

    class Meta:
        verbose_name = _('Ингредиент')

    def __str__(self):
        return f"{self.name} ({self.unit_of_measurement})"
