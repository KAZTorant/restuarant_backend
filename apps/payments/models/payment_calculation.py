from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
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
    payments = models.ManyToManyField(
        'Payment', verbose_name=_("Ödənişlər"), blank=True,
        related_name='payment_calculations'
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

    def get_payments(self):
        """Get all payments within this calculation's date/time range"""
        # Return saved payments if they exist, otherwise calculate dynamically
        if self.payments.exists():
            return self.payments.all()
        
        # Fallback to dynamic calculation (for old records)
        from apps.payments.models import Payment
        
        start_datetime = datetime.combine(self.start_date, self.start_time)
        end_datetime = datetime.combine(self.end_date, self.end_time)
        
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
        if timezone.is_naive(end_datetime):
            end_datetime = timezone.make_aware(end_datetime)
        
        return Payment.objects.filter(
            paid_at__gte=start_datetime,
            paid_at__lte=end_datetime
        ).prefetch_related('orders__order_items__meal', 'table', 'paid_by', 'payment_methods')

    def get_product_sales_summary(self):
        """Get summary of all products sold in payments during this period"""
        from collections import defaultdict

        from apps.orders.models import OrderItem
        
        product_summary = defaultdict(lambda: {'quantity': 0, 'total': 0})
        
        payments = self.get_payments()
        
        for payment in payments:
            for order in payment.orders.all():
                for item in order.order_items.all():
                    product_summary[item.meal.name]['quantity'] += item.quantity
                    product_summary[item.meal.name]['total'] += float(item.price)
        
        # Convert to sorted list
        return sorted(
            [
                {
                    'name': name, 
                    'quantity': data['quantity'], 
                    'total': data['total']
                }
                for name, data in product_summary.items()
            ],
            key=lambda x: x['total'],
            reverse=True
        )
