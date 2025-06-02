from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IngredientAPIViewSet

router = DefaultRouter()
router.register(
    'ingredients',
    IngredientAPIViewSet,
    basename='ingredients',
)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
