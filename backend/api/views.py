from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets, permissions

from api.serializers import IngredientSerializer, PlatformUserSerializer
from ingredients.models import Ingredient
from users.models import PlatformUser


class PageLimitPagination(PageNumberPagination):
    default_page_size = 10
    page_size_param = "limit"
    max_page_size = 100


class PlatformUserManagementController(BaseUserViewSet):
    queryset = PlatformUser.objects.all()
    pagination_class = PageLimitPagination
    serializer_class = PlatformUserSerializer


class IngredientAPIViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        ingredient_name_filter = self.request.query_params.get('name')
        return queryset.filter(name__istartswith=ingredient_name_filter)[:10]
