from django.db.models import Prefetch
from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from djoser.views import UserViewSet as BaseUserViewSet

from .serializers import (
    IngredientSerializer,
    PlatformUserSerializer,
    RecipeCreateUpdateSerializer,
    RecipeReadSerializer,
    FavoriteRecipeSerializer,
    ShoppingCartSerializer,
)
from ingredients.models import Ingredient
from users.models import PlatformUser
from recipes.models import Recipe, RecipeIngredient, ShoppingCart, FavoriteRecipe, RecipeCategory


class StandardResultsPagination(PageNumberPagination):
    default_page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_description = "Номер страницы"
    page_size_query_description = "Количество элементов на странице"


class UserViewSet(BaseUserViewSet):
    queryset = PlatformUser.objects.all()
    serializer_class = PlatformUserSerializer
    pagination_class = StandardResultsPagination
    search_fields = ('email', 'username')
    ordering_fields = ('id', 'date_joined')
    http_method_names = ['get', 'post', 'patch', 'delete']


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    pagination_class = None
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        search_term = self.request.query_params.get('name', '').strip()

        if not search_term:
            return Ingredient.objects.none()

        return Ingredient.objects.filter(
            name__istartswith=search_term
        ).order_by('name')[:10]


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author')
    pagination_class = StandardResultsPagination
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeReadSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        user = self.request.user

        if author_id := params.get('author'):
            queryset = queryset.filter(author_id=author_id)

        if category_id := params.get('category'):
            queryset = queryset.filter(categories__id=category_id)

        if difficulty := params.get('difficulty'):
            queryset = queryset.filter(difficulty=difficulty)

        if user.is_authenticated:
            if params.get('is_in_shopping_cart') in ['1', 'true']:
                queryset = queryset.filter(shopping_carts__user=user)
            if params.get('is_favorited') in ['1', 'true']:
                queryset = queryset.filter(favorites__user=user)

        return queryset.prefetch_related(
            Prefetch(
                'ingredients_through',
                queryset=RecipeIngredient.objects.select_related('ingredient')
            ),
            Prefetch(
                'categories',
                queryset=RecipeCategory.objects.only(
                    'name', 'color_code', 'icon')
            )
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            self.permission_denied(
                self.request,
                message="Вы можете изменять только свои рецепты"
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            self.permission_denied(
                self.request,
                message="Вы можете удалять только свои рецепты"
            )
        instance.delete()

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download-shopping-cart',
        name='download-shopping-cart'
    )
    def download_shopping_cart(self, request):
        user = request.user

        if not ShoppingCart.objects.filter(user=user).exists():
            return Response(
                {'detail': 'Ваша корзина покупок пуста'},
                status=status.HTTP_404_NOT_FOUND
            )

        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_carts__user=user
        ).select_related('ingredient').order_by('ingredient__name')

        aggregated = {}
        for item in ingredients:
            key = (item.ingredient.name, item.ingredient.unit_of_measurement)
            if key not in aggregated:
                aggregated[key] = {
                    'total': 0,
                    'notes': set()
                }
            aggregated[key]['total'] += item.amount
            if item.notes:
                aggregated[key]['notes'].add(item.notes)

        content_lines = []
        for (name, unit), data in aggregated.items():
            line = f"{name} - {data['total']} {unit}"
            if data['notes']:
                notes = ', '.join(sorted(data['notes']))
                line += f" ({notes})"
            content_lines.append(line)

        content = "Список покупок:\n\n" + "\n".join(content_lines)

        response = HttpResponse(
            content,
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class UserRecipeRelationViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    lookup_field = 'recipe_id'
    lookup_url_kwarg = 'recipe_id'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(serializer.data)
        )

    def destroy(self, request, recipe_id):
        obj = get_object_or_404(self.get_queryset(), recipe_id=recipe_id)
        self.perform_destroy(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteRecipeViewSet(UserRecipeRelationViewSet):
    serializer_class = FavoriteRecipeSerializer
    queryset = FavoriteRecipe.objects.all()


class ShoppingCartViewSet(UserRecipeRelationViewSet):
    serializer_class = ShoppingCartSerializer
    queryset = ShoppingCart.objects.all()
