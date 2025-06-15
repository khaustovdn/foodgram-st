import pytest
from django.db import IntegrityError
from users.models import ChefSubscription
from recipes.models import BookmarkedRecipe, ShoppingListRecipe


@pytest.mark.django_db
def test_duplicate_subscription_raises_error(test_user, recipe_author):
    ChefSubscription.objects.create(author=recipe_author, follower=test_user)
    with pytest.raises(IntegrityError):
        ChefSubscription.objects.create(
            author=recipe_author, follower=test_user
        )


@pytest.mark.django_db
def test_duplicate_favorite_raises_error(test_user, sample_recipe):
    BookmarkedRecipe.objects.create(user=test_user, recipe=sample_recipe)
    with pytest.raises(IntegrityError):
        BookmarkedRecipe.objects.create(user=test_user, recipe=sample_recipe)


@pytest.mark.django_db
def test_duplicate_shopping_item_raises_error(test_user, sample_recipe):
    ShoppingListRecipe.objects.create(user=test_user, recipe=sample_recipe)
    with pytest.raises(IntegrityError):
        ShoppingListRecipe.objects.create(user=test_user, recipe=sample_recipe)
