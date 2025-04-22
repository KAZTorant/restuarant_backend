from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.payments.models.pay_table_orders import Payment


class Receipt(models.Model):
    class ReceiptType(models.TextChoices):
        CUSTOMER = 'customer', _('Müştəri üçün')
        PREPERATION_PLACE = 'preperation_places', _('Hazırlanma yeri üçün')
        SHIFT_SUMMARY = 'shift_summary', _("Növbə yekunu")
        Z_SUMMRY = 'z_summary', _("Z Hesabat")

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Çap tarixi")
    )
    type = models.CharField(
        max_length=20, choices=ReceiptType.choices, verbose_name=_("Çek növü")
    )
    text = models.TextField(verbose_name=_("Çek mətnləri"))
    orders = models.ManyToManyField(
        "orders.Order", blank=True, related_name='receipts')

    payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_("Əlaqəli ödəniş")
    )
    printer_response_status_code = models.IntegerField(
        default=200, verbose_name=_("Printer cavab status kodu")
    )

    class Meta:
        verbose_name = _("Çek")
        verbose_name_plural = _("Çeklər")

    def __str__(self):
        return f"{self.get_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
