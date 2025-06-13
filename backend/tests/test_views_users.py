# tests/test_views_users.py
import pytest
import base64
from django.urls import reverse
from django.core.files.base import ContentFile
from rest_framework import status
from users.models import ChefSubscription


@pytest.mark.django_db
def test_toggle_user_subscription(drf_client, test_user, recipe_author):
    drf_client.force_authenticate(user=test_user)
    url = reverse("users-manage-subscription", kwargs={"id": recipe_author.pk})

    # Subscribe to author
    response = drf_client.post(url)
    assert response.status_code == status.HTTP_201_CREATED
    assert ChefSubscription.objects.filter(
        follower=test_user, author=recipe_author
    ).exists()

    # Unsubscribe from author
    response = drf_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not ChefSubscription.objects.filter(
        follower=test_user, author=recipe_author
    ).exists()


MINIMAL_AVATAR = base64.b64decode(
    "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
)


@pytest.mark.django_db
def test_update_user_avatar(drf_client, test_user):
    drf_client.force_authenticate(user=test_user)
    url = reverse("users-manage-profile-picture")

    # Upload new avatar
    avatar_file = ContentFile(MINIMAL_AVATAR, name="test.gif")
    response = drf_client.put(url, {"avatar": avatar_file}, format="multipart")
    assert response.status_code == status.HTTP_200_OK

    # Delete avatar
    response = drf_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    test_user.refresh_from_db()
    assert not test_user.avatar
