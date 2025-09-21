from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from apps.commons.models import DateTimeModel
from apps.orders.models import Order

User = get_user_model()


class WorkPeriodConfig(models.Model):
    """Configuration for work periods (start/end times)"""

    name = models.CharField(max_length=100, verbose_name="Ad")
    start_time = models.TimeField(verbose_name="Başlama vaxtı")
    end_time = models.TimeField(verbose_name="Bitmə vaxtı")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "İş Dövrü Konfiqurasiyası"
        verbose_name_plural = "İş Dövrü Konfiqurasiyaları"

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class ReportManager(models.Manager):
    """Manager for Report model"""

    def get_or_create_for_date(self, date):
        """Get or create Report for given date using active WorkPeriodConfig"""
        from datetime import time

        # Get active work period config
        config = WorkPeriodConfig.objects.filter(is_active=True).first()
        if not config:
            # Create default config: 12:00 afternoon to 02:00 midnight
            config = WorkPeriodConfig.objects.create(
                name="Standart İş Dövrü",
                start_time=time(12, 0),  # 12:00 PM
                end_time=time(2, 0),     # 02:00 AM next day
                is_active=True
            )

        # Calculate start and end datetime based on config
        start_datetime = datetime.combine(date, config.start_time)
        start_datetime = timezone.make_aware(start_datetime)

        # If end_time < start_time, it's next day
        if config.end_time < config.start_time:
            end_date = date + timedelta(days=1)
        else:
            end_date = date

        end_datetime = datetime.combine(end_date, config.end_time)
        end_datetime = timezone.make_aware(end_datetime)

        # Get or create report
        report, created = self.get_or_create(
            work_period_config=config,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            defaults={
                'total_amount': Decimal('0.00'),
                'cash_total': Decimal('0.00'),
                'card_total': Decimal('0.00'),
                'other_total': Decimal('0.00'),
                'unpaid_total': Decimal('0.00'),
            }
        )

        # Update report with current orders if it exists
        if not created:
            report.update_totals()

        return report, created


class Report(DateTimeModel, models.Model):
    """Automatic work period reports based on WorkPeriodConfig"""

    work_period_config = models.ForeignKey(
        WorkPeriodConfig,
        on_delete=models.PROTECT,
        verbose_name="İş Dövrü Konfiqurasiyası"
    )
    start_datetime = models.DateTimeField(
        verbose_name="Başlama tarixi və vaxtı")
    end_datetime = models.DateTimeField(verbose_name="Bitmə tarixi və vaxtı")

    # Financial totals (updated dynamically)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ümumi məbləğ"
    )
    cash_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Nağd ümumi"
    )
    card_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Kartla ümumi"
    )
    other_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Digər ödənişlər"
    )
    unpaid_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ödənilməmiş ümumi"
    )

    # Orders relationship (filtered based on WorkPeriodConfig)
    orders = models.ManyToManyField(
        Order,
        blank=True,
        related_name="reports",
        verbose_name="Sifarişlər"
    )

    objects = ReportManager()

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reportlar"
        unique_together = [
            'work_period_config',
            'start_datetime',
            'end_datetime'
        ]

    def update_totals(self):
        """Update financial totals based on orders in this period"""
        from apps.payments.models import Payment, PaymentMethod

        # Get ALL orders in this period (including soft-deleted/reported ones)
        period_orders = Order.objects.all_orders().filter(
            created_at__gte=self.start_datetime,
            created_at__lte=self.end_datetime
        )

        # Update orders relationship
        self.orders.set(period_orders)

        # Calculate paid orders
        paid_orders = period_orders.filter(is_paid=True)
        unpaid_orders = period_orders.filter(is_paid=False)

        # Get payments for paid orders
        all_payments = Payment.objects.filter(
            orders__in=paid_orders).distinct()

        # Initialize totals
        cash_total = Decimal('0.00')
        card_total = Decimal('0.00')
        other_total = Decimal('0.00')

        # Calculate payment totals
        for payment in all_payments:
            if payment.payment_methods.exists():
                change_amount = payment.change or Decimal('0.00')

                for method in payment.payment_methods.all():
                    method_amount = method.amount

                    # Subtract change from cash if applicable
                    if method.payment_type == 'cash' and change_amount > 0:
                        method_amount = method_amount - change_amount
                        change_amount = Decimal('0.00')

                    if method.payment_type == 'cash':
                        cash_total += method_amount
                    elif method.payment_type == 'card':
                        card_total += method_amount
                    elif method.payment_type == 'other':
                        other_total += method_amount
            else:
                # Fallback to old payment_type field
                if payment.payment_type == 'cash':
                    cash_total += payment.final_price
                elif payment.payment_type == 'card':
                    card_total += payment.final_price
                elif payment.payment_type == 'other':
                    other_total += payment.final_price

        # Calculate unpaid total
        unpaid_total = unpaid_orders.aggregate(
            total=models.Sum('total_price')
        )['total'] or Decimal('0.00')

        # Update fields
        self.cash_total = cash_total
        self.card_total = card_total
        self.other_total = other_total
        self.unpaid_total = unpaid_total
        self.total_amount = cash_total + card_total + other_total + unpaid_total

        self.save()

    def __str__(self):
        return f"{self.work_period_config.name} - {self.start_datetime}"
