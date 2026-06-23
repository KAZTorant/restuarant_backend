from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.commons.models import TenantModel

User = get_user_model()


class PaymentCalculation(TenantModel, models.Model):
    start_date = models.DateField(_("Başlanğıc tarixi"))
    end_date = models.DateField(_("Son tarixi"))
    start_time = models.TimeField(_("Başlanğıc saatı"))
    end_time = models.TimeField(_("Son saatı"))
    total_amount = models.DecimalField(
        _("Sifarişlərin cəmi"), max_digits=10, decimal_places=2
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
    
    @property
    def extra_paid_amount(self):
        """Calculate extra amount paid (tips, change, etc.)"""
        total_paid = self.cash_amount + self.card_amount + self.other_amount
        return total_paid - self.total_amount

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

        from apps.orders.models import Order, OrderItem
        
        product_summary = defaultdict(lambda: {'quantity': 0, 'total': 0})
        
        payments = self.get_payments()
        
        for payment in payments:
            # Access the through model directly to bypass the Order manager filter
            through_model = payment.orders.through
            through_entries = through_model.objects.filter(payment=payment)
            
            for entry in through_entries:
                # Get the order using all_orders() to include deleted orders
                try:
                    order = Order.objects.all_orders().get(id=entry.order_id)
                    
                    # Use all_order_items() to get items even from deleted orders
                    for item in OrderItem.objects.all_order_items().filter(order=order):
                        product_summary[item.meal.name]['quantity'] += item.quantity
                        product_summary[item.meal.name]['total'] += float(item.price)
                except Order.DoesNotExist:
                    # Order was permanently deleted
                    continue
        
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

    def get_waiter_payments_summary(self):
        """Get summary of payments grouped by waiter"""
        from collections import defaultdict
        from decimal import Decimal

        from apps.orders.models import Order
        
        waiter_summary = defaultdict(lambda: {
            'total_amount': Decimal(0),
            'payment_count': 0,
            'order_count': 0,
            'cash_amount': Decimal(0),
            'card_amount': Decimal(0),
            'other_amount': Decimal(0),
            'waiter_name': '',
            'waiter_id': None
        })
        
        payments = self.get_payments()
        
        for payment in payments:
            # Get all orders for this payment
            through_model = payment.orders.through
            through_entries = through_model.objects.filter(payment=payment)
            
            # Track waiters for this payment
            payment_waiters = set()
            
            for entry in through_entries:
                try:
                    order = Order.objects.all_orders().get(id=entry.order_id)
                    if order.waitress:
                        payment_waiters.add((order.waitress.id, order.waitress.get_full_name() or order.waitress.username))
                except Order.DoesNotExist:
                    continue
            
            # If no waiter found, skip this payment or assign to "Unknown"
            if not payment_waiters:
                waiter_key = 'unknown'
                waiter_summary[waiter_key]['waiter_name'] = 'Ofisiant təyin edilməyib'
                waiter_summary[waiter_key]['waiter_id'] = None
            else:
                # If multiple waiters for one payment, we'll count it for the first one
                # or split it equally (for now, let's assign to first waiter)
                waiter_id, waiter_name = list(payment_waiters)[0]
                waiter_key = f'waiter_{waiter_id}'
                waiter_summary[waiter_key]['waiter_name'] = waiter_name
                waiter_summary[waiter_key]['waiter_id'] = waiter_id
            
            # Add payment details
            waiter_summary[waiter_key]['payment_count'] += 1
            waiter_summary[waiter_key]['order_count'] += len(through_entries)
            waiter_summary[waiter_key]['total_amount'] += payment.final_price
            
            # Calculate amounts by payment type
            if payment.payment_methods.exists():
                for method in payment.payment_methods.all():
                    if method.payment_type == 'cash':
                        waiter_summary[waiter_key]['cash_amount'] += method.amount
                    elif method.payment_type == 'card':
                        waiter_summary[waiter_key]['card_amount'] += method.amount
                    else:
                        waiter_summary[waiter_key]['other_amount'] += method.amount
            else:
                if payment.payment_type == 'cash':
                    waiter_summary[waiter_key]['cash_amount'] += payment.paid_amount
                elif payment.payment_type == 'card':
                    waiter_summary[waiter_key]['card_amount'] += payment.paid_amount
                else:
                    waiter_summary[waiter_key]['other_amount'] += payment.paid_amount
        
        # Convert to sorted list
        return sorted(
            [
                {
                    'waiter_id': data['waiter_id'],
                    'waiter_name': data['waiter_name'],
                    'total_amount': data['total_amount'],
                    'payment_count': data['payment_count'],
                    'order_count': data['order_count'],
                    'cash_amount': data['cash_amount'],
                    'card_amount': data['card_amount'],
                    'other_amount': data['other_amount'],
                }
                for key, data in waiter_summary.items()
            ],
            key=lambda x: x['total_amount'],
            reverse=True
        )
