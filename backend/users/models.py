# backend/users/models.py

from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator


class CulinaryUser(AbstractUser):
    """Custom user model for culinary platform."""

    class Meta(AbstractUser.Meta):
        ordering = ("username",)
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        constraints = [
            models.UniqueConstraint(fields=["email"], name="unique_user_email"),
            models.UniqueConstraint(
                fields=["username"], name="unique_user_username"
            ),
        ]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    username_validator = RegexValidator(
        regex=r"^[\w.@+-]+$",
        message=(
            "Имя пользователя должно содержать только буквы,"
            "цифры и символы @.+-_ "
        ),
        code="invalid_username",
    )

    username = models.CharField(
        verbose_name=_("Имя пользователя"),
        max_length=128,
        unique=True,
        validators=[
            username_validator,
        ],
    )
    email = models.EmailField(
        verbose_name=_("Адрес электронной почты"),
        unique=True,
        max_length=256,
    )
    first_name = models.CharField(
        verbose_name=_("Имя"),
        max_length=128,
    )
    last_name = models.CharField(
        verbose_name=_("Фамилия"),
        max_length=128,
    )
    avatar = models.ImageField(
        verbose_name=_("Изображение профиля"),
        upload_to="image/users/%Y/%m/%d/",
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return self.email


class ChefSubscription(models.Model):
    """Represents subscription relationship between users."""

    class Meta:
        ordering = ("follower",)
        verbose_name = _("Подписка на автора")
        verbose_name_plural = _("Подписки на авторов")
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "author"], name="unique_chef_subscription"
            ),
        ]

    follower = models.ForeignKey(
        CulinaryUser,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name=_("Подписчик"),
    )
    author = models.ForeignKey(
        CulinaryUser,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name=_("Автор"),
    )

    def __str__(self) -> str:
        return f"{self.follower} → {self.author}"
