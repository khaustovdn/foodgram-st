import pytest
from django.contrib.auth import get_user_model
from ingredients.models import CulinaryIngredient
from recipes.models import CulinaryRecipe, RecipeIngredient

User = get_user_model()


@pytest.fixture
def drf_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def recipe_author():
    return User.objects.create_user(
        email="log@example.com",
        username="log",
        password="qwerew123432",
        first_name="log",
        last_name="log",
    )


@pytest.fixture
def test_user():
    return User.objects.create_user(
        email="khaustovdn@example.com",
        username="khaustovdn",
        password="1qazwsxedc1",
        first_name="khaustovdn",
        last_name="khaustovdn",
    )


@pytest.fixture
def test_ingredient():
    return CulinaryIngredient.objects.create(
        name="Ingredient", measurement_unit="g"
    )


@pytest.fixture
def sample_recipe(recipe_author, test_ingredient):
    recipe = CulinaryRecipe.objects.create(
        name="Recipe",
        text="Text",
        cooking_time=90,
        author=recipe_author,
    )
    RecipeIngredient.objects.create(
        recipe=recipe, ingredient=test_ingredient, amount=100
    )
    return recipe
