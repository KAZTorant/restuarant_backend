from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from apps.tables.models import Table
# from apps.orders.models.order import Order

User = get_user_model()


class PaymentMethod(models.Model):
    class PaymentType(models.TextChoices):
        CASH = 'cash', _('Nağd')
        CARD = 'card', _('Kart')
        OTHER = 'other', _('Digər')

    payment = models.ForeignKey(
        'Payment', on_delete=models.CASCADE, related_name='payment_methods'
    )
    amount = models.DecimalField(
        _("Məbləğ"), max_digits=10, decimal_places=2
    )
    payment_type = models.CharField(
        _("Ödəniş növü"), max_length=20, choices=PaymentType.choices
    )
    created_at = models.DateTimeField(_("Yaradılma tarixi"), auto_now_add=True)

    class Meta:
        verbose_name = _("Ödəniş növü")
        verbose_name_plural = _("Ödəniş növləri")

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.amount}₼"


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        CASH = 'cash', _('Nağd')
        CARD = 'card', _('Kart')
        OTHER = 'other', _('Digər')

    table = models.ForeignKey(
        Table, on_delete=models.CASCADE, verbose_name=_("Masa")
    )
    orders = models.ManyToManyField(
        "orders.Order", verbose_name=_("Sifarişlər"))
    total_price = models.DecimalField(
        _("Ümumi məbləğ"), max_digits=10, decimal_places=2
    )
    discount_amount = models.DecimalField(
        _("Endirim"), max_digits=10, decimal_places=2, default=0
    )
    discount_comment = models.CharField(
        _("Endirim səbəbi"), max_length=255, blank=True
    )
    final_price = models.DecimalField(
        _("Son məbləğ"), max_digits=10, decimal_places=2
    )
    paid_amount = models.DecimalField(
        _("Ödənilən məbləğ"), max_digits=10, decimal_places=2
    )
    change = models.DecimalField(
        _("Qaytarılacaq məbləğ"), max_digits=10, decimal_places=2, default=0
    )
    payment_type = models.CharField(
        _("Ödəniş növü"), max_length=20, choices=PaymentType.choices
    )
    paid_by = models.ForeignKey(User, verbose_name=_(
        "Operator"), on_delete=models.SET_NULL, null=True
    )
    paid_at = models.DateTimeField(_("Ödəmə tarixi"), auto_now_add=True)

    class Meta:
        verbose_name = _("Ödəmə")
        verbose_name_plural = _("Ödəmələr")

    def __str__(self):
        return f"{self.table} üçün {self.final_price}₼ ödəniş"

    @property
    def payment_methods_display(self):
        return ", ".join([
            f"{method.get_payment_type_display()}: {method.amount}₼"
            for method in self.payment_methods.all()
        ])
