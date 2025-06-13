# backend/api/serializers.py

import base64
from typing import Any, Dict, List, Type
from django.db import models
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers

from ingredients.models import CulinaryIngredient
from recipes.models import (
    CulinaryRecipe,
    RecipeIngredient,
    BookmarkedRecipe,
    ShoppingListRecipe,
)
from users.models import CulinaryUser, ChefSubscription


class Base64ImageSerializerField(serializers.ImageField):
    """Custom serializer field for handling base64-encoded image uploads."""

    def to_internal_value(self, data):
        """Convert base64 image string to ContentFile."""
        if isinstance(data, str) and data.startswith("data:image"):
            try:
                # Extract format and encoded data
                format_str, img_str = data.split(";base64,")
                extension = format_str.split("/")[-1]

                # Decode base64 string
                decoded_file = base64.b64decode(img_str)

                # Create ContentFile with temporary name
                return ContentFile(decoded_file, name=f"temp.{extension}")
            except (ValueError, TypeError, IndexError):
                raise serializers.ValidationError(
                    _("Некорректный формат изображения")
                )
        return super().to_internal_value(data)


class UserProfilePictureSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile pictures."""

    class Meta:
        model = CulinaryUser
        fields = ("avatar",)

    avatar = Base64ImageSerializerField(required=True)

    def update(
        self, instance: CulinaryUser, validated_data: Dict[str, Any]
    ) -> CulinaryUser:
        """Update user's profile picture."""
        profile_picture = validated_data.get("avatar")
        if not profile_picture:
            raise serializers.ValidationError(
                {"avatar": _("Обязательное изображение")}
            )

        instance.avatar = profile_picture
        instance.save()
        return instance


class CulinaryUserProfileSerializer(BaseUserSerializer):
    """Extended user profile serializer."""

    class Meta(BaseUserSerializer.Meta):
        model = CulinaryUser
        fields = (*BaseUserSerializer.Meta.fields, "is_subscribed", "avatar")

    is_subscribed = serializers.SerializerMethodField(
        method_name="get_is_subscribed"
    )
    avatar = serializers.SerializerMethodField(
        method_name="get_profile_picture_url"
    )

    def get_profile_picture_url(self, user: CulinaryUser) -> str:
        """Get absolute URL for user's profile picture."""
        if user.avatar:
            return user.avatar.url
        return None

    def get_is_subscribed(self, author: CulinaryUser) -> bool:
        """Check if current user is subscribed to the author."""
        current_user = self.context.get("request").user

        return (
            current_user
            and current_user.is_authenticated
            and ChefSubscription.objects.filter(
                author=author, follower=current_user
            ).exists()
        )


class CulinaryUserWithRecipesSerializer(BaseUserSerializer):
    """User profile serializer with embedded recipe information."""

    class Meta(BaseUserSerializer.Meta):
        fields = (*BaseUserSerializer.Meta.fields, "recipes", "recipes_count")

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    def get_recipes(self, user: CulinaryUser) -> List[Dict]:
        """Get paginated list of user's recipes."""
        request = self.context.get("request")
        queryset = user.recipes.all()

        # Apply pagination limit if provided
        if recipes_limit := request.query_params.get("recipes_limit"):
            try:
                queryset = queryset[: int(recipes_limit)]
            except ValueError:
                pass

        return CulinaryRecipeBriefSerializer(
            queryset, many=True, context=self.context
        ).data

    def get_recipes_count(self, user: CulinaryUser) -> int:
        """Get total count of user's recipes."""
        return user.recipes.count()


class CulinaryIngredientSerializer(serializers.ModelSerializer):
    """Serializer for culinary ingredients with validation."""

    class Meta:
        model = CulinaryIngredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer for recipe-ingredient relationships."""

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")

    id = serializers.PrimaryKeyRelatedField(
        queryset=CulinaryIngredient.objects.all(), source="ingredient.id"
    )
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )


class CulinaryRecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating recipes."""

    class Meta:
        model = CulinaryRecipe
        fields = ("id", "name", "text", "cooking_time", "image", "ingredients")

    id = serializers.IntegerField(read_only=True)
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=True,
        error_messages={"required": _("Обязательное поле")},
    )
    image = Base64ImageSerializerField(required=True)

    def validate_ingredients(self, value):
        """Унифицированная проверка ингредиентов"""
        if len(value) < 1:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент"
            )
        errors = []
        seen_ingredients = set()
        for i, item in enumerate(value):
            amount = item.get("amount")
            ingredient_id = item.get("id")
            if not ingredient_id:
                errors.append(f"Ингредиент #{i + 1}: отсутствует ID")
            if amount is not None:
                try:
                    amount = int(amount)
                    if amount < 1:
                        errors.append(
                            f"Ингредиент #{i + 1}: "
                            "количество должно быть не менее 1"
                        )
                except (TypeError, ValueError):
                    errors.append(
                        f"Ингредиент #{i + 1}: неверный формат количества"
                    )
            else:
                errors.append(f"Ингредиент #{i + 1}: отсутствует количество")
            if ingredient_id:
                if ingredient_id in seen_ingredients:
                    errors.append(
                        f"Ингредиент #{i + 1}: "
                        f"дубликат ингредиента с ID {ingredient_id}"
                    )
                seen_ingredients.add(ingredient_id)
        if seen_ingredients:
            existing_ids = set(
                CulinaryIngredient.objects.filter(
                    id__in=seen_ingredients
                ).values_list("id", flat=True)
            )
            missing_ids = seen_ingredients - existing_ids
            if missing_ids:
                errors.append(
                    f"Несуществующие ингредиенты: {list(missing_ids)}"
                )
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate_cooking_time(self, value: int) -> int:
        """Validate cooking time is at least 1 minute."""
        if value < 1:
            raise serializers.ValidationError(
                _("Время приготовления должно быть не менее 1 минуты")
            )
        return value

    def _create_recipe_ingredients(
        self, recipe: CulinaryRecipe, ingredients_data: List[Dict]
    ) -> None:
        """Create RecipeIngredient instances in bulk."""
        recipe_ingredient_objs = []
        for item in ingredients_data:
            ingredient_id = item.get("id")
            amount = item.get("amount")
            ingredient = CulinaryIngredient.objects.get(id=ingredient_id)
            recipe_ingredient_objs.append(
                RecipeIngredient(
                    recipe=recipe, ingredient=ingredient, amount=amount
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredient_objs)

    def create(self, validated_data: Dict) -> CulinaryRecipe:
        """Create a new recipe with ingredients."""
        ingredients_data = validated_data.pop("ingredients")
        recipe = CulinaryRecipe.objects.create(
            author=self.context["request"].user, **validated_data
        )
        self._create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(
        self, instance: CulinaryRecipe, validated_data: Dict
    ) -> CulinaryRecipe:
        """Update existing recipe and its ingredients."""
        if "ingredients" not in validated_data:
            raise serializers.ValidationError(
                {"ingredients": "Обязательное поле"}
            )
        ingredients_data = validated_data.pop("ingredients")

        # Update recipe fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        # Replace existing ingredients
        if ingredients_data:
            instance.recipes_ingredients.all().delete()
            self._create_recipe_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance: CulinaryRecipe) -> Dict:
        """Return detailed representation after create/update."""
        return CulinaryRecipeDetailSerializer(
            instance, context=self.context
        ).data


class CulinaryRecipeDetailSerializer(serializers.ModelSerializer):
    """Detailed recipe serializer with full relationships."""

    class Meta:
        model = CulinaryRecipe
        fields = (
            "id",
            "name",
            "text",
            "cooking_time",
            "image",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
        )

    ingredients = serializers.SerializerMethodField()
    author = CulinaryUserProfileSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField(method_name="get_image_url")
    text = serializers.CharField()

    def get_author(self, obj):
        """Get serialized author data for the recipe."""
        from . import CulinaryUserProfileSerializer

        return CulinaryUserProfileSerializer(
            obj.author, context=self.context
        ).data

    def get_ingredients(self, obj):
        """Get formatted ingredients data for the recipe."""
        return [
            {
                "id": ri.ingredient.id,
                "name": ri.ingredient.name,
                "measurement_unit": ri.ingredient.measurement_unit,
                "amount": ri.amount,
            }
            for ri in obj.recipes_ingredients.all()
        ]

    def get_image_url(self, recipe: CulinaryRecipe) -> str:
        """Get absolute URL for recipe image."""
        request = self.context.get("request")
        if recipe.image:
            return (
                request.build_absolute_uri(recipe.image.url)
                if request
                else recipe.image.url
            )
        return None

    def _get_user_recipe_relation_status(
        self, recipe: CulinaryRecipe, relation_model: Type[models.Model]
    ) -> bool:
        """Check if current user has a specific relationship with the recipe."""
        request = self.context.get("request")
        user = (
            request.user if request and request.user.is_authenticated else None
        )

        return bool(
            user
            and relation_model.objects.filter(user=user, recipe=recipe).exists()
        )

    def get_is_favorited(self, recipe: CulinaryRecipe) -> bool:
        """Check if recipe is favorited by current user."""
        return self._get_user_recipe_relation_status(recipe, BookmarkedRecipe)

    def get_is_in_shopping_cart(self, recipe: CulinaryRecipe) -> bool:
        """Check if recipe is in current user's shopping list."""
        return self._get_user_recipe_relation_status(recipe, ShoppingListRecipe)


class CulinaryRecipeBriefSerializer(serializers.ModelSerializer):
    """Minimal recipe serializer for list views and embeddings."""

    class Meta:
        model = CulinaryRecipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields

    image = serializers.SerializerMethodField(method_name="get_image_url")

    def get_image_url(self, recipe: CulinaryRecipe) -> str:
        """Get absolute URL for recipe image."""
        request = self.context.get("request")
        if recipe.image:
            return (
                request.build_absolute_uri(recipe.image.url)
                if request
                else recipe.image.url
            )
        return None


class UserRecipeInteractionSerializer(serializers.ModelSerializer):
    """Base serializer for user-recipe relationships."""

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        fields = ("id", "user", "recipe")
        read_only_fields = ("id", "user")

    def validate(self, attrs: Dict) -> Dict:
        """Validate that user doesn't create duplicate relationships."""
        user = attrs["user"]
        recipe = attrs["recipe"]

        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(_("Этот рецепт уже добавлен"))

        return attrs


class RecipeBookmarkSerializer(UserRecipeInteractionSerializer):
    """Serializer for bookmarking recipes."""

    class Meta(UserRecipeInteractionSerializer.Meta):
        model = BookmarkedRecipe


class ShoppingListSerializer(UserRecipeInteractionSerializer):
    """Serializer for adding recipes to shopping lists."""

    class Meta(UserRecipeInteractionSerializer.Meta):
        model = ShoppingListRecipe
