from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from ingredients.models import Ingredient
from users.models import PlatformUser


class RecipeCategory(models.Model):
    name = models.CharField(
        _('Название категории'),
        max_length=50,
        unique=True,
        help_text=_('Укажите название категории (например: Завтраки, Десерты)')
    )
    color_code = models.CharField(
        _('Цветовой код'),
        max_length=10,
        validators=[
            RegexValidator(
                regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message=_('Введите корректный HEX-код цвета (например: #FF5733)')
            )
        ],
        help_text=_('HEX-код цвета для визуального выделения категории')
    )
    icon = models.CharField(
        _('Иконка'),
        max_length=30,
        blank=True,
        null=True,
        help_text=_('Код иконки из библиотеки (например: fas fa-utensils)')
    )
    slug = models.SlugField(
        _('Идентификатор'),
        max_length=50,
        unique=True,
        help_text=_(
            'Уникальный идентификатор для URL (только латинские буквы, цифры, дефисы)')
    )
    description = models.TextField(
        _('Описание'),
        blank=True,
        help_text=_('Краткое описание категории')
    )
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='subcategories',
        verbose_name=_('Родительская категория'),
        help_text=_('Выберите родительскую категорию для создания иерархии')
    )

    class Meta:
        verbose_name = _('Категория рецептов')
        verbose_name_plural = _('Категории рецептов')
        ordering = ('name',)
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    DIFFICULTY_LEVELS = (
        ('easy', _('Легкий')),
        ('medium', _('Средний')),
        ('hard', _('Сложный')),
    )

    name = models.CharField(
        _('Название рецепта'),
        max_length=255,
        help_text=_('Укажите название вашего рецепта')
    )
    description = models.TextField(
        _('Описание рецепта'),
        blank=True,
        null=True,
        help_text=_('Подробно опишите процесс приготовления')
    )
    cooking_time = models.PositiveSmallIntegerField(
        _('Время приготовления (минуты)'),
        validators=[MinValueValidator(1)],
    )
    difficulty = models.CharField(
        _('Уровень сложности'),
        max_length=10,
        choices=DIFFICULTY_LEVELS,
        default='medium',
        help_text=_('Выберите уровень сложности приготовления')
    )
    servings = models.PositiveSmallIntegerField(
        _('Количество порций'),
        validators=[MinValueValidator(1)],
        default=1,
    )
    image = models.ImageField(
        _('Изображение блюда'),
        upload_to='recipes/%Y/%m/%d/',
        help_text=_('Загрузите изображение готового блюда')
    )
    author = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='authored_recipes',
        verbose_name=_('Автор рецепта'),
        default=1
    )
    categories = models.ManyToManyField(
        RecipeCategory,
        related_name='recipes',
        verbose_name=_('Категории'),
        help_text=_('Выберите подходящие категории для рецепта')
    )
    created_at = models.DateTimeField(
        _('Дата создания'),
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        _('Дата обновления'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('Рецепт')
        verbose_name_plural = _('Рецепты')
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'author'],
                name='unique_author_recipe',
                violation_error_message=_(
                    'У вас уже есть рецепт с таким названием')
            ),
        ]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['cooking_time']),
            models.Index(fields=['created_at']),
            models.Index(fields=['difficulty']),
        ]

    def __str__(self):
        return f'{self.name} ({self.author.username})'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients_through',
        verbose_name=_('Рецепт')
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name=_('Ингредиент')
    )
    amount = models.DecimalField(
        _('Количество'),
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text=_('Количество ингредиента для рецепта')
    )
    notes = models.CharField(
        _('Дополнительные указания'),
        max_length=100,
        blank=True,
        help_text=_('Особенности использования (например: мелко нарезать)')
    )

    class Meta:
        verbose_name = _('Ингредиент рецепта')
        verbose_name_plural = _('Ингредиенты рецептов')
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
                violation_error_message=_(
                    'Этот ингредиент уже добавлен в рецепт')
            ),
        ]
        ordering = ['ingredient__name']

    def __str__(self):
        return f'{self.ingredient.name} - {self.amount} {self.ingredient.unit}'


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name=_('Рецепт')
    )
    created_at = models.DateTimeField(
        _('Дата создания'),
        default=timezone.now
    )

    class Meta:
        abstract = True
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(app_label)s_%(class)s_unique_user_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class FavoriteRecipe(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = _('Избранный рецепт')
        verbose_name_plural = _('Избранные рецепты')
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]


class ShoppingCart(UserRecipeRelation):
    planned_cooking_date = models.DateField(
        _('Планируемая дата приготовления'),
        blank=True,
        null=True,
        help_text=_('Когда вы планируете приготовить это блюдо')
    )

    class Meta(UserRecipeRelation.Meta):
        verbose_name = _('Корзина покупок')
        verbose_name_plural = _('Корзины покупок')
        indexes = [
            models.Index(fields=['user', 'planned_cooking_date']),
        ]
