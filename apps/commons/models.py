from django.db import models


class DateTimeModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True, blank=True, null=True, verbose_name="tarix", editable=True)
    updated_at = models.DateTimeField(
        auto_now=True, blank=True, null=True, verbose_name="Yeniləndi")

    class Meta:
        abstract = True


class TenantModel(models.Model):
    restaurant = models.ForeignKey(
        'tenants.Restaurant',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        verbose_name='Restoran',
    )

    class Meta:
        abstract = True
