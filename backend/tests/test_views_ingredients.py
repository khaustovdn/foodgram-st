import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
def test_search_ingredients_by_name(drf_client, test_ingredient):
    url = reverse("ingredient-list")
    response = drf_client.get(url, {"name": "test"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["name"] == "Ingredient"


@pytest.mark.django_db
def test_get_ingredient_details(drf_client, test_ingredient):
    url = reverse("ingredient-detail", kwargs={"pk": test_ingredient.pk})
    response = drf_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["measurement_unit"] == "g"
