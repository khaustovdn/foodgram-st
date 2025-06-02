from django.core.exceptions import ValidationError
from django.db import transaction
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from ingredients.models import Ingredient
from users.models import AuthorSubscription
from recipes.models import (
    Recipe,
    RecipeIngredient,
    FavoriteRecipe,
    ShoppingCart,
    RecipeCategory
)


class PlatformUserSerializer(BaseUserSerializer):
    has_active_subscription = serializers.SerializerMethodField(
        help_text="Проверка активной подписки текущего пользователя на автора"
    )

    class Meta(BaseUserSerializer.Meta):
        model = BaseUserSerializer.Meta.model
        fields = (*BaseUserSerializer.Meta.fields, 'has_active_subscription')
        read_only_fields = ('has_active_subscription',)

    def get_has_active_subscription(self, author) -> bool:
        request = self.context.get('request')
        current_user = getattr(request, 'user', None) if request else None

        return (
            current_user is not None and
            current_user.is_authenticated and
            AuthorSubscription.objects.filter(
                author=author,
                follower=current_user
            ).exists()
        )


class RecipeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeCategory
        fields = ('id', 'name', 'color_code', 'icon', 'slug')
        read_only_fields = fields
        extra_kwargs = {
            'color_code': {
                'help_text': 'HEX-код цвета для визуального выделения категории'
            },
            'icon': {
                'help_text': 'Код иконки из библиотеки (например: fas fa-utensils)'
            }
        }


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'unit_of_measurement')
        read_only_fields = fields


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
        error_messages={
            'does_not_exist': 'Ингредиент с ID={pk_value} не существует'
        }
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    unit = serializers.CharField(
        source='ingredient.unit_of_measurement',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'unit', 'amount', 'notes')
        extra_kwargs = {
            'amount': {
                'min_value': 0.01,
                'error_messages': {
                    'min_value': 'Количество не может быть меньше 0.01'
                },
                'help_text': 'Количество ингредиента для рецепта'
            },
            'notes': {
                'allow_blank': True,
                'help_text': 'Особенности использования (например: мелко нарезать)'
            }
        }


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='ingredients_through',
        help_text="Список ингредиентов с указанием количества и заметками"
    )
    categories = serializers.PrimaryKeyRelatedField(
        queryset=RecipeCategory.objects.all(),
        many=True,
        help_text="Список ID категорий рецепта"
    )
    difficulty = serializers.ChoiceField(
        choices=Recipe.DIFFICULTY_LEVELS,
        help_text="Уровень сложности приготовления"
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'description', 'cooking_time', 'difficulty', 'servings',
            'image', 'ingredients', 'categories'
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'cooking_time': {
                'min_value': 1,
                'error_messages': {
                    'min_value': 'Время приготовления должно быть не менее 1 минуты'
                }
            },
            'servings': {
                'min_value': 1,
                'error_messages': {
                    'min_value': 'Количество порций должно быть не менее 1'
                }
            },
            'image': {
                'required': True,
                'help_text': 'Изображение готового блюда'
            }
        }

    def _validate_ingredients(self, ingredients_data: list) -> None:
        if not ingredients_data:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент")

        errors = []
        seen_ingredient_ids = set()
        ingredient_ids = set()

        for index, item in enumerate(ingredients_data, start=1):
            ingredient = item.get('ingredient')
            amount = item.get('amount', 0)

            if not ingredient:
                errors.append(f"Ингредиент #{index}: отсутствует ID")
                continue

            ingredient_id = ingredient.id
            ingredient_ids.add(ingredient_id)

            if ingredient_id in seen_ingredient_ids:
                errors.append(
                    f"Ингредиент #{index}: дубликат ингредиента (ID={
                        ingredient_id})"
                )
            seen_ingredient_ids.add(ingredient_id)

            if amount < 0.01:
                errors.append(
                    f"Ингредиент #{
                        index}: количество должно быть не менее 0.01"
                )

        existing_ids = set(Ingredient.objects.filter(
            id__in=ingredient_ids
        ).values_list('id', flat=True))

        if missing_ids := ingredient_ids - existing_ids:
            errors.append(
                "Несуществующие ингредиенты: " +
                ", ".join(str(id) for id in sorted(missing_ids))
            )

        if errors:
            raise serializers.ValidationError(errors)

    def _validate_categories(self, categories_data: list) -> None:
        if not categories_data:
            raise serializers.ValidationError(
                "Добавьте хотя бы одну категорию")

        category_ids = [category.id for category in categories_data]
        existing_count = RecipeCategory.objects.filter(
            id__in=category_ids).count()

        if existing_count != len(category_ids):
            raise serializers.ValidationError(
                "Одна или несколько категорий не существуют"
            )

    def validate(self, data: dict) -> dict:
        ingredients_data = data.get('ingredients_through', [])
        categories_data = data.get('categories', [])

        self._validate_ingredients(ingredients_data)
        self._validate_categories(categories_data)

        return data

    @transaction.atomic
    def create(self, validated_data: dict) -> Recipe:
        ingredients_data = validated_data.pop('ingredients_through')
        categories_data = validated_data.pop('categories')

        recipe = Recipe.objects.create(
            **validated_data,
            author=self.context['request'].user
        )
        recipe.categories.set(categories_data)
        self._create_recipe_ingredients(recipe, ingredients_data)

        return recipe

    @transaction.atomic
    def update(self, instance: Recipe, validated_data: dict) -> Recipe:
        ingredients_data = validated_data.pop('ingredients_through', None)
        categories_data = validated_data.pop('categories', None)

        if categories_data is not None:
            instance.categories.set(categories_data)

        if ingredients_data is not None:
            instance.ingredients_through.all().delete()
            self._create_recipe_ingredients(instance, ingredients_data)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance

    def _create_recipe_ingredients(
        self,
        recipe: Recipe,
        ingredients_data: list
    ) -> None:
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount'],
                notes=item.get('notes', '')
            ) for item in ingredients_data
        ])

    def to_representation(self, instance: Recipe) -> dict:
        return RecipeReadSerializer(
            instance,
            context=self.context
        ).data


class RecipeReadSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='ingredients_through',
        read_only=True
    )
    categories = RecipeCategorySerializer(many=True, read_only=True)
    author = PlatformUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField(
        help_text="Находится ли рецепт в избранном у текущего пользователя"
    )
    is_in_shopping_cart = serializers.SerializerMethodField(
        help_text="Находится ли рецепт в корзине покупок у текущего пользователя"
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'description', 'cooking_time', 'difficulty', 'servings', 'image',
            'author', 'ingredients', 'categories',
            'is_favorited', 'is_in_shopping_cart', 'created_at', 'updated_at'
        )
        read_only_fields = fields

    def _get_relation_status(
        self,
        recipe: Recipe,
        relation_model
    ) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None

        return (
            user is not None and
            user.is_authenticated and
            relation_model.objects.filter(
                user=user,
                recipe=recipe
            ).exists()
        )

    def get_is_favorited(self, recipe: Recipe) -> bool:
        return self._get_relation_status(recipe, FavoriteRecipe)

    def get_is_in_shopping_cart(self, recipe: Recipe) -> bool:
        return self._get_relation_status(recipe, ShoppingCart)


class BaseUserRecipeSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
        write_only=True
    )
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
        write_only=True,
        error_messages={
            'does_not_exist': 'Рецепт с ID={pk_value} не существует'
        }
    )

    class Meta:
        abstract = True
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=None,
                fields=('user', 'recipe'),
                message='Рецепт уже связан с пользователем'
            )
        ]

    def validate(self, attrs: dict) -> dict:
        if self.Meta.model.objects.filter(**attrs).exists():
            raise ValidationError(
                {"recipe": "Рецепт уже связан с пользователем"}
            )
        return attrs

    def to_representation(self, instance) -> dict:
        return RecipeReadSerializer(
            instance.recipe,
            context=self.context
        ).data


class FavoriteRecipeSerializer(BaseUserRecipeSerializer):
    class Meta(BaseUserRecipeSerializer.Meta):
        model = FavoriteRecipe


class ShoppingCartSerializer(BaseUserRecipeSerializer):
    planned_cooking_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Планируемая дата приготовления блюда"
    )

    class Meta(BaseUserRecipeSerializer.Meta):
        model = ShoppingCart
        fields = BaseUserRecipeSerializer.Meta.fields + \
            ('planned_cooking_date',)
