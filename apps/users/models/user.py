from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.commons.models import DateTimeModel


class User(DateTimeModel, AbstractUser):
    username = models.CharField(max_length=150, unique=False)

    TYPE_CHOICES = (
        ('waitress', 'Ofisiant'),
        ('captain_waitress', 'Kapitan Ofisiant'),
        ('admin', 'Administrator'),
        ('restaurant', 'Restaurant Sahibi'),
    )

    type = models.CharField(
        choices=TYPE_CHOICES,
        max_length=32,
        blank=True,
        null=True,
    )
    restaurant = models.ForeignKey(
        'tenants.Restaurant',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        verbose_name='Restoran',
        help_text='Superuser üçün boş buraxın.',
    )

    class Meta:
        verbose_name = 'Ofisiant və Menecer'
        verbose_name_plural = 'Ofisiant və Menecerlər'
        silenced_system_checks = ['auth.E003']
        constraints = [
            models.UniqueConstraint(
                fields=['restaurant', 'username'],
                name='unique_restaurant_username',
                condition=models.Q(restaurant__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username}"
