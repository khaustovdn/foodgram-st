from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator


class PlatformUser(AbstractUser):
    username = models.CharField(
        _('Имя пользователя'),
        max_length=128,
        unique=True,
        validators=[
            MinLengthValidator(
                3,
                message=_('Имя пользователя должно содержать минимум 3 символа')
            ),
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
                message=_(
                    'Имя пользователя может содержать только буквы, цифры и символы @/./+/-/_')
            )
        ],
        help_text=_(
            'Обязательное поле. Не более 150 символов. Только буквы, цифры и @/./+/-/_.')
    )
    email = models.EmailField(
        _('Адрес электронной почты'),
        unique=True,
        max_length=256,
        error_messages={
            'unique': _('Пользователь с таким email уже существует.')
        }
    )
    first_name = models.CharField(
        _('Имя'),
        max_length=128,
        blank=False,
        validators=[MinLengthValidator(2)]
    )
    last_name = models.CharField(
        _('Фамилия'),
        max_length=128,
        blank=False,
        validators=[MinLengthValidator(2)]
    )
    bio = models.TextField(
        _('Биография'),
        blank=True,
        max_length=1000,
        help_text=_('Расскажите немного о себе')
    )
    profile_picture = models.ImageField(
        _('Аватар'),
        upload_to='users/profile_pics/%Y/%m/%d/',
        blank=True,
        null=True
    )

    class Meta(AbstractUser.Meta):
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ('-date_joined',)
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name


class AuthorSubscription(models.Model):
    follower = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name=_('Подписчик'),
        help_text=_('Пользователь, который подписывается')
    )
    author = models.ForeignKey(
        PlatformUser,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name=_('Автор'),
        help_text=_('Пользователь, на которого подписываются'),
        default=1
    )
    created_at = models.DateTimeField(
        _('Дата подписки'),
        default=timezone.now
    )

    class Meta:
        verbose_name = _('Подписка на автора')
        verbose_name_plural = _('Подписки на авторов')
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'author'],
                name='unique_subscription',
                violation_error_message=_('Вы уже подписаны на этого автора')
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F('author')),
                name='prevent_self_follow',
                violation_error_message=_('Нельзя подписаться на самого себя')
            ),
        ]
        indexes = [
            models.Index(fields=['follower', 'author']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.follower} → {self.author}'

    def clean(self):
        if self.follower == self.author:
            raise ValidationError(
                {'author': _('Нельзя подписаться на самого себя')}
            )
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
