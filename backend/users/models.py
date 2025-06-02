from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models


class PlatformUser(AbstractUser):
    email = models.EmailField(
        _('Адрес электронной почты'),
        unique=True,
        max_length=256,
    )

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class AuthorSubscription(models.Model):
    follower = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=_('Подписчик'),
    )
    following = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name=_('Автор'),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_subscription',
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F('following')),
                name='prevent_self_follow'
            ),
        ]

    def __str__(self):
        return f"{self.follower} → {self.following}"
