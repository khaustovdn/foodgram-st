# backend/api/views.py

import logging

from django.db.models import Sum
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from djoser.views import UserViewSet as DjoserUserViewSet

from .serializers import (
    CulinaryUserProfileSerializer,
    UserProfilePictureSerializer,
    CulinaryIngredientSerializer,
    CulinaryRecipeCreateUpdateSerializer,
    CulinaryRecipeDetailSerializer,
    CulinaryRecipeBriefSerializer,
    ShoppingListSerializer,
    CulinaryUserWithRecipesSerializer,
    RecipeBookmarkSerializer,
)
from ingredients.models import CulinaryIngredient
from users.models import CulinaryUser, ChefSubscription
from recipes.models import (
    CulinaryRecipe,
    RecipeIngredient,
    BookmarkedRecipe,
    ShoppingListRecipe,
)

logger = logging.getLogger(__name__)


class StandardResultsPagination(PageNumberPagination):
    """Custom pagination configuration with default settings."""

    default_page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100


class UserProfileViewSet(DjoserUserViewSet):
    """Viewset for managing user profiles and related actions."""

    queryset = CulinaryUser.objects.all()
    pagination_class = StandardResultsPagination
    permission_classes = [AllowAny]
    serializer_class = CulinaryUserProfileSerializer

    @action(detail=False, methods=["GET"], permission_classes=[IsAuthenticated])
    def current_user_profile(self, request):
        """Retrieve profile information for the authenticated user."""
        return super().me(request)

    @action(
        methods=["PUT", "DELETE"],
        detail=False,
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
    )
    def manage_profile_picture(self, request):
        """Update or delete the authenticated user's profile picture."""
        user = request.user

        if request.method == "PUT":
            serializer = UserProfilePictureSerializer(
                user,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"avatar": user.avatar.url}, status=status.HTTP_200_OK
            )

        elif request.method == "DELETE":
            if not user.avatar:
                return Response(
                    {"detail": "Изображение профиля не найдено"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.avatar.delete()
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def user_subscriptions(self, request):
        """Retrieve authors the current user is subscribed to."""
        subscribed_authors = CulinaryUser.objects.filter(
            followers__follower=request.user
        )

        page = self.paginate_queryset(subscribed_authors)
        serializer = CulinaryUserWithRecipesSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["POST", "DELETE"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def manage_subscription(self, request, id=None):
        """Create or delete subscription to an author."""
        author = self.get_object()
        current_user = request.user

        if author == current_user:
            return Response(
                {"detail": "Нельзя подписаться на самого себя"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription_exists = ChefSubscription.objects.filter(
            author=author, follower=current_user
        ).exists()

        if request.method == "POST":
            if subscription_exists:
                return Response(
                    {"detail": "Вы уже подписаны на этого автора"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ChefSubscription.objects.create(
                author=author, follower=current_user
            )
            serializer = CulinaryUserWithRecipesSerializer(
                author, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            if not subscription_exists:
                return Response(
                    {"detail": "Не подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ChefSubscription.objects.filter(
                author=author, follower=current_user
            ).first().delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientSearchViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for searching culinary ingredients."""

    serializer_class = CulinaryIngredientSerializer
    pagination_class = None
    http_method_names = ["get"]
    permission_classes = (AllowAny,)

    def get_queryset(self):
        """Filter ingredients by search query."""
        queryset = CulinaryIngredient.objects.all()
        search_term = self.request.query_params.get("name")

        if search_term:
            queryset = queryset.filter(name__istartswith=search_term)

        return queryset


class CulinaryRecipeViewSet(viewsets.ModelViewSet):
    """Viewset for managing recipes and related user actions."""

    queryset = CulinaryRecipe.objects.all()
    pagination_class = StandardResultsPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Select serializer based on action."""
        logger.debug(f"get_serializer_class called for action: {self.action}")
        if self.action in ["list", "retrieve"]:
            return CulinaryRecipeDetailSerializer
        return CulinaryRecipeCreateUpdateSerializer

    def get_queryset(self):
        """Apply filters to recipe queryset based on query parameters."""
        logger.debug(
            f"get_queryset called with params: {self.request.query_params}"
        )
        queryset = super().get_queryset()
        params = self.request.query_params
        user = self.request.user

        # Filter by author
        if author_id := params.get("author"):
            logger.debug(f"Filtering by author_id: {author_id}")
            queryset = queryset.filter(author_id=author_id)

        # User-specific filters
        if user.is_authenticated:
            # Shopping list filter
            if params.get("is_in_shopping_cart") in ["1", "true"]:
                logger.debug("Filtering by shopping cart")
                queryset = queryset.filter(shoppinglist__user=user)

            # Favorites filter
            if params.get("is_favorited") in ["1", "true"]:
                logger.debug("Filtering by favorites")
                queryset = queryset.filter(bookmarked__user=user)
        else:
            logger.debug("Anonymous user access")

        return queryset

    def perform_update(self, serializer):
        """Verify user has permission to update recipe."""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied(
                "Вы можете редактировать только свои собственные рецепты"
            )
        serializer.save()

    def perform_destroy(self, instance):
        """Verify user has permission to delete recipe."""
        if instance.author != self.request.user:
            raise PermissionDenied(
                "Вы можете удалять только свои собственные рецепты"
            )
        instance.delete()

    @action(
        detail=True,
        methods=["GET"],
        url_path="get-link",
    )
    def generate_shareable_link(self, request, pk=None):
        """Generate a shareable link for the specified recipe."""
        recipe = self.get_object()
        shareable_link = request.build_absolute_uri(
            f"/recipes/short-link/{recipe.id}/"
        )

        return Response(
            {"short-link": shareable_link}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["POST", "DELETE"],
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def manage_shopping_cart(self, request, pk=None):
        """Add or remove recipe from user's shopping list."""
        return self._handle_user_recipe_relation(
            request,
            pk,
            ShoppingListRecipe,
            ShoppingListSerializer,
            "Рецепт уже в списке покупок",
            "Рецепт не найден в списке покупок",
        )

    @action(
        detail=True,
        methods=["POST", "DELETE"],
        permission_classes=[IsAuthenticated],
        url_path="favorite",
    )
    def manage_favorites(self, request, pk=None):
        """Add or remove recipe from user's favorites."""
        return self._handle_user_recipe_relation(
            request,
            pk,
            BookmarkedRecipe,
            RecipeBookmarkSerializer,
            "Рецепт уже в избранном",
            "Рецепт не найден в избранном",
        )

    def _handle_user_recipe_relation(
        self,
        request,
        _recipe_id,
        relation_model,
        _serializer_class,
        exists_message,
        not_found_message,
    ):
        """Generic handler for user-recipe relationships."""
        recipe = self.get_object()
        user = request.user
        relation_exists = relation_model.objects.filter(
            user=user, recipe=recipe
        ).exists()

        if request.method == "POST":
            if relation_exists:
                return Response(
                    {"detail": exists_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            relation_model.objects.create(user=user, recipe=recipe)
            serializer = CulinaryRecipeBriefSerializer(
                recipe, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            if not relation_exists:
                return Response(
                    {"detail": not_found_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            relation_model.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        """Generate and download shopping list as text file."""
        logger.debug(
            f"download_shopping_cart called by user: {request.user.id}"
        )
        try:
            # Aggregate ingredients from shopping list recipes
            recipes = ShoppingListRecipe.objects.filter(
                user=request.user
            ).values_list("recipe", flat=True)
            logger.debug(f"Found {len(recipes)} recipes in shopping cart")

            ingredients = (
                RecipeIngredient.objects.filter(recipe__in=recipes)
                .values("ingredient__name", "ingredient__measurement_unit")
                .annotate(total_amount=Sum("amount"))
                .order_by("ingredient__name")
            )

            if not ingredients:
                return Response(
                    {"detail": "Список покупок пуст"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate text content
            content_lines = [
                f"{item['ingredient__name']} "
                f"({item['ingredient__measurement_unit']}): "
                f"{item['total_amount']}"
                for item in ingredients
            ]
            content = "\n".join(content_lines)

            # Create file response
            response = HttpResponse(content, content_type="text/plain")
            response["Content-Disposition"] = (
                'attachment; filename="shopping_cart.txt"'
            )
            return response
        except Exception as e:
            logger.error(
                f"Error in download_shopping_cart: {str(e)}", exc_info=True
            )
            return Response(
                {"detail": "Произошла ошибка при формировании списка покупок"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
