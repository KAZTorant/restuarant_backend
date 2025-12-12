from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class PaymentCalculation(models.Model):
    start_date = models.DateField(_("Başlanğıc tarixi"))
    end_date = models.DateField(_("Son tarixi"))
    start_time = models.TimeField(_("Başlanğıc saatı"))
    end_time = models.TimeField(_("Son saatı"))
    total_amount = models.DecimalField(
        _("Ümumi məbləğ"), max_digits=10, decimal_places=2
    )
    payment_count = models.PositiveIntegerField(
        _("Ödəniş sayı"), default=0
    )
    cash_amount = models.DecimalField(
        _("Nağd məbləğ"), max_digits=10, decimal_places=2, default=0
    )
    card_amount = models.DecimalField(
        _("Kart məbləğ"), max_digits=10, decimal_places=2, default=0
    )
    other_amount = models.DecimalField(
        _("Digər məbləğ"), max_digits=10, decimal_places=2, default=0
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_("Yaratdı")
    )
    created_at = models.DateTimeField(_("Yaradılma tarixi"), auto_now_add=True)

    class Meta:
        verbose_name = _("Ödəniş hesablaması")
        verbose_name_plural = _("Ödəniş hesablamaları")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.start_date} - {self.end_date} | {self.total_amount}₼"

    @property
    def date_range_display(self):
        return f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}"

    @property
    def time_range_display(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
