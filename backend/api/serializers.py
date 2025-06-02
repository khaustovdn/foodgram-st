from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers

from ingredients.models import Ingredient
from users.models import PlatformUser, AuthorSubscription


class PlatformUserSerializer(BaseUserSerializer):
    has_active_subscription = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = PlatformUser
        fields = (
            *BaseUserSerializer.Meta.fields,
            'has_active_subscription',
        )

    def get_has_active_subscription(self, user_object):
        if not (current_user := (self.context.get("request") or {}).get("user")):
            return False
        return AuthorSubscription.objects.filter(
            author=user_object,
            follower=current_user
        ).exists()


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'unit_of_measurement',
        )
