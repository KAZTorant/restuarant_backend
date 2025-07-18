import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
from collections import Counter
from django.db.models import Sum, Count, Q

from simple_history.models import HistoricalRecords

from apps.commons.models import DateTimeModel
from apps.orders.models import Order
from apps.payments.models import Payment

User = get_user_model()


class StatisticsManager(models.Manager):
    # === Existing summary methods ===
    def calculate_per_waitress(self, date=None):
        if not date:
            date = timezone.localdate() - timezone.timedelta(days=1)
        waitresses_orders = Order.objects.filter(
            created_at__date=date,
            is_paid=True,
            waitress__isnull=False
        ).values(
            'waitress', 'waitress__username', 'waitress__first_name', 'waitress__last_name'
        ).annotate(total_price=Sum('total_price'))
        for order in waitresses_orders:
            waitress_info = f"{order['waitress__username']} - {order['waitress__first_name']} {order['waitress__last_name']}"
            self.update_or_create(
                title='per_waitress',
                date=date,
                waitress_info=waitress_info,
                defaults={'total': order['total_price']}
            )

    def calculate_daily(self, date=None):
        if not date:
            date = timezone.localdate() - timezone.timedelta(days=1)
        self.calculate_per_waitress(date=date)
        existing_stat = self.filter(title='daily', date=date).first()
        if not existing_stat:
            start_of_day = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.min.time()))
            end_of_day = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.max.time()))
            daily_total = Order.objects.filter(
                created_at__range=(start_of_day, end_of_day),
                is_paid=True
            ).aggregate(sum=Sum('total_price'))['sum'] or 0
            if not daily_total:
                return
            existing_stat, _ = self.update_or_create(
                title='daily', date=date,
                defaults={'total': daily_total}
            )
        return existing_stat

    def calculate_monthly(self, date=None):
        if not date:
            date = timezone.localdate() - timezone.timedelta(days=1)
        first = date.replace(day=1)
        last_day = date.replace(
            day=models.functions.datetime_extract('day', date))
        for n in range((last_day - first).days + 1):
            self.calculate_daily(first + timezone.timedelta(days=n))
        total = self.filter(title='daily', date__range=[first, last_day]).aggregate(
            sum=Sum('total'))['sum'] or 0
        if not total:
            return
        return self.update_or_create(title='monthly', date=first, defaults={'total': total})

    def calculate_yearly(self, date=None):
        if not date:
            date = timezone.localdate() - timezone.timedelta(days=1)
        first = date.replace(month=1, day=1)
        for month in range(1, date.month + 1):
            self.calculate_monthly(first.replace(month=month))
        total = self.filter(title='monthly', date__year=date.year).aggregate(
            sum=Sum('total'))['sum'] or 0
        if not total:
            return
        return self.update_or_create(title='yearly', date=first, defaults={'total': total})

    def start_shift(self, user):
        if self.filter(is_closed=False).exists():
            raise ValidationError("Açıq növbən var.")
        last = self.filter(is_closed=True).order_by(
            '-end_time').first()
        initial = last.remaining_cash if last else Decimal('0.00')
        return self.create(title="till_now", started_by=user, start_time=timezone.now(), initial_cash=initial)

    def end_shift(
        self, shift, user,
        withdrawn_amount=Decimal('0.00'),
        withdrawn_notes='',
    ):
        if shift.started_by != user:
            raise ValidationError(
                "Növbəni bitirə bilmək üçün onu açan admin olmalısınız.")
        if shift.is_closed:
            raise ValidationError("Növbə artıq bağlanıb.")

        if withdrawn_amount > shift.cash:
            raise ValidationError(
                f"Çıxarılan məbləğ nağd ümumi məbləği ötə bilməz. {withdrawn_amount} > {shift.cash}"
            )

        shift.withdrawn_amount = withdrawn_amount
        shift.withdrawn_notes = withdrawn_notes
        shift.remaining_cash = shift.cash - withdrawn_amount
        shift.end_time = timezone.now()
        shift.ended_by = user
        shift.is_closed = True
        shift.is_z_checked = True
        shift.save()

        for o in shift.orders.all():
            o.is_deleted = True
            o.save()
        # shift.orders.update(is_deleted=True)
        return shift

    def delete_orders_for_statistics_day(self, date):
        self.calculate_daily(date)
        start = timezone.make_aware(timezone.datetime.combine(
            date, timezone.datetime.min.time()))
        end = timezone.make_aware(timezone.datetime.combine(
            date, timezone.datetime.max.time()))
        orders = Order.objects.filter(
            created_at__range=(start, end), is_paid=True)
        count = orders.count()
        for o in orders:
            o.is_deleted = True
            o.save()
        # orders.update(is_deleted=True)
        return count

    def calculate_till_now(self, user=None):
        """
        Update the existing 'till_now' Statistics record with fresh
        cumulative totals and payment‐type breakdowns; do nothing if none exists.
        """
        # 1) Find the existing till_now stat
        stat = self.filter(
            title='till_now',
            is_z_checked=False,
            is_closed=False,
            started_by=user
        ).first()
        # logging.error(f"TOTAL: TILL NOW, {user} {stat}")
        if not stat:
            return None
        # logging.error("Found existing 'till_now' statistics record.")

        # 2) All paid orders
        orders = Order.objects.filter(is_paid=True)
        # logging.error(f"Fetched {orders.count()} paid orders.")

        # 3) All payments linked to those orders
        all_payments = Payment.objects.filter(orders__in=orders)
        payments = all_payments.distinct()
        # logging.error(
        #     f"Filtered payments linked to paid orders: {payments.count()} found.")

        # Identify non-distinct payment IDs
        # payment_ids = list(all_payments.values_list("id", flat=True))
        # duplicates = [pid for pid, count in Counter(
        #     payment_ids).items() if count > 1]
        # if duplicates:
        #     logging.warning(
        #         f"Non-distinct (duplicated across orders) Payment IDs: {duplicates}")

        # Manual breakdown and accumulation
        cash_total = Decimal('0.00')
        card_total = Decimal('0.00')
        other_total = Decimal('0.00')

        cash_count = 0
        card_count = 0
        other_count = 0

        cash_discount = Decimal('0.00')
        card_discount = Decimal('0.00')
        other_discount = Decimal('0.00')

        total_total_price = Decimal('0.00')
        total_final_price = Decimal('0.00')
        total_discount = Decimal('0.00')

        # Log detailed cash payment table header
        # logging.error(
        #     "┌────────────┬───────────────┬──────────────┬────────────────┐")
        # logging.error(
        #     "│ Payment ID │ Total Price   │ Final Price  │ Discount Amount│")
        # logging.error(
        #     "├────────────┼───────────────┼──────────────┼────────────────┤")

        for payment in payments:
            total_total_price += payment.total_price
            total_final_price += payment.final_price
            total_discount += payment.discount_amount

            # Check if payment has payment methods, otherwise use payment_type
            if payment.payment_methods.exists():
                # Use the new payment methods
                # Calculate change amount (assumed returned in cash)
                change_amount = payment.change or Decimal('0.00')

                for method in payment.payment_methods.all():
                    method_amount = method.amount

                    # If this is cash and there's change, subtract the change from cash
                    if method.payment_type == Payment.PaymentType.CASH and change_amount > 0:
                        method_amount = method_amount - change_amount
                        # Only subtract once from the first cash method
                        change_amount = Decimal('0.00')

                    if method.payment_type == Payment.PaymentType.CASH:
                        cash_total += method_amount
                        cash_discount += payment.discount_amount * \
                            (method_amount / payment.final_price) if payment.final_price > 0 else Decimal('0.00')
                        cash_count += 1
                    elif method.payment_type == Payment.PaymentType.CARD:
                        card_total += method_amount
                        card_discount += payment.discount_amount * \
                            (method_amount / payment.final_price) if payment.final_price > 0 else Decimal('0.00')
                        card_count += 1
                    elif method.payment_type == Payment.PaymentType.OTHER:
                        other_total += method_amount
                        other_discount += payment.discount_amount * \
                            (method_amount / payment.final_price) if payment.final_price > 0 else Decimal('0.00')
                        other_count += 1
            else:
                # Fallback to old payment_type field
                if payment.payment_type == Payment.PaymentType.CASH:
                    cash_total += payment.final_price
                    cash_discount += payment.discount_amount
                    cash_count += 1
                    logging.error(
                        f"│ {str(payment.id).rjust(10)} │ {str(payment.total_price).rjust(13)} │ "
                        f"{str(payment.final_price).rjust(12)} │ {str(payment.discount_amount).rjust(14)} │"
                    )
                elif payment.payment_type == Payment.PaymentType.CARD:
                    card_total += payment.final_price
                    card_discount += payment.discount_amount
                    card_count += 1
                elif payment.payment_type == Payment.PaymentType.OTHER:
                    other_total += payment.final_price
                    other_discount += payment.discount_amount
                    other_count += 1

        # logging.error(
        #     "├────────────┼───────────────┼──────────────┼────────────────┤")
        # logging.error(
        #     f"│ {'TOTAL'.rjust(10)} │ {str(total_total_price).rjust(13)} │ "
        #     f"{str(total_final_price).rjust(12)} │ {str(total_discount).rjust(14)} │"
        # )
        # logging.error(
        #     "└────────────┴───────────────┴──────────────┴────────────────┘")

        # logging.error(
        #     f"Breakdown - Cash: {cash_total} ({cash_count} payments, {cash_discount} discount), "
        #     f"Card: {card_total} ({card_count} payments, {card_discount} discount), "
        #     f"Other: {other_total} ({other_count} payments, {other_discount} discount)"
        # )

        # 4) Overwrite all relevant fields
        stat.total = (cash_total + card_total +
                      other_total) + stat.initial_cash
        stat.date = timezone.localdate()
        stat.started_by = user or stat.started_by
        stat.cash_total = cash_total
        stat.card_total = card_total
        stat.other_total = other_total
        stat.withdrawn_amount = Decimal('0.00')
        stat.remaining_cash = cash_total + stat.initial_cash - stat.withdrawn_amount
        stat.save()
        # logging.error("Updated statistics record fields and saved.")

        # 5) Refresh linked orders
        stat.orders.set(orders)
        # logging.error("Linked orders updated for the statistics record.")

        return stat


class Statistics(DateTimeModel, models.Model):
    TITLE_CHOICES = (
        ("till_now", "Hesabat"), ("daily", "Günlük"),
        ("monthly", "Aylıq"), ("yearly", "İllik"),
        ("per_waitress", "Ofisianta görə")
    )
    title = models.CharField(
        max_length=32,
        choices=TITLE_CHOICES,
        default="daily",
        verbose_name="Başlıq"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ümumi məbləğ"
    )
    date = models.DateField(
        default=timezone.now,
        verbose_name="Tarix"
    )
    waitress_info = models.CharField(
        max_length=90,
        blank=True,
        null=True,
        verbose_name="Ofisiant"
    )
    is_z_checked = models.BooleanField(
        default=False,
        verbose_name="Hesabat təsdiqləndi?"
    )
    orders = models.ManyToManyField(
        Order,
        blank=True,
        related_name="statistics",
        verbose_name="Sifarişlər"
    )

    # --- Shift fields ---
    started_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='shifts_started',
        verbose_name='Növbəni açan'
    )
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Növbənin başlanma vaxtı'
    )
    initial_cash = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Başlanğıc nağd'
    )
    ended_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='shifts_ended',
        verbose_name='Növbəni bağlayan'
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Növbənin bitmə vaxtı'
    )
    is_closed = models.BooleanField(
        default=False,
        verbose_name='Növbə bağlandı?'
    )
    cash_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Nağd qazanılmış'
    )
    card_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Kartla ümumi'
    )
    other_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Digər ödənişlər'
    )
    withdrawn_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Çıxarılan məbləğ'
    )
    withdrawn_notes = models.TextField(
        blank=True,
        verbose_name='Bağlanma Qeydi'
    )

    remaining_cash = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Qalan nağd'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Başlanma Qeydi'
    )
    history = HistoricalRecords()

    objects = StatisticsManager()

    class Meta:
        verbose_name = "Statistika"
        verbose_name_plural = "Statistikalar 📊"

    @property
    def cash(self):
        return round(self.cash_total + self.initial_cash, 2)

    def __str__(self):
        status = 'Bağlandı' if self.is_closed else 'Açıq'
        return f"{self.started_by} tərəfindən {self.start_time:%Y-%m-%d %H:%M} tarixində başlayan növbə ({status})"
