from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IngredientSearchViewSet, UserProfileViewSet, CulinaryRecipeViewSet


router = DefaultRouter()
router.register(
    "ingredients",
    IngredientSearchViewSet,
    basename="ingredients",
)
router.register("users", UserProfileViewSet, basename="users")
router.register("recipes", CulinaryRecipeViewSet, basename="recipes")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
]
