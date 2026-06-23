from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.commons.models import DateTimeModel, TenantModel
from apps.orders.models.statistics import Statistics

User = get_user_model()


class Summary(TenantModel, DateTimeModel, models.Model):
    """
    Model for date-range summary reports of restaurant statistics.
    No additional name field needed - we use date range for identification.
    """
    start_date = models.DateField(
        verbose_name="Başlanğıc tarixi"
    )
    end_date = models.DateField(
        verbose_name="Bitiş tarixi"
    )
    statistics = models.ManyToManyField(
        Statistics,
        blank=True,
        related_name="summaries",
        verbose_name="Hesabatlar"
    )
    cash_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Nağd məbləğ"
    )
    card_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Kart məbləği"
    )
    other_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Digər ödənişlər"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ümumi məbləğ"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='summaries',
        verbose_name='Hesabatı yaradan'
    )

    class Meta:
        verbose_name = "Ümumi hesabat"
        verbose_name_plural = "Ümumi hesabatlar 📊"
        ordering = ['-created_at']

    def __str__(self):
        return f"Hesabat: {self.start_date} - {self.end_date}"

    @property
    def date_range_display(self):
        """Return a formatted date range string."""
        return f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}"
