from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from apps.commons.models import DateTimeModel
from apps.meals.models import Meal
from apps.orders.models.order_deletion import OrderItemDeletionLog
from apps.tables.models import Table
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import now
from simple_history.models import HistoricalRecords


User = get_user_model()

# Model for Order


class OrderManager(models.Manager):
    def all_orders(self):
        return super().get_queryset()

    def get_queryset(self):
        # Override the default queryset to exclude deleted objects
        return super().get_queryset().filter(is_deleted=False)


class Order(DateTimeModel, models.Model):
    table = models.ForeignKey(
        Table,
        related_name='orders',
        on_delete=models.CASCADE,
        verbose_name="Stol"
    )
    meals = models.ManyToManyField(
        Meal,
        through='OrderItem',
        verbose_name="Yemək"
    )
    is_paid = models.BooleanField(default=False, verbose_name="Ödənilib")
    is_check_printed = models.BooleanField(
        default=False, verbose_name="Çek çıxarılıb")
    is_deleted = models.BooleanField(default=False)
    is_main = models.BooleanField(default=False)

    waitress = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        blank=True,
        null=True,
        verbose_name="Ofisiant"
    )
    total_price = models.DecimalField(
        default=0, max_digits=10, decimal_places=2,
        verbose_name="Ümumi"
    )

    customer_count = models.PositiveIntegerField(
        default=1,
        verbose_name="Müştəri sayı"
    )

    history = HistoricalRecords()
    objects = OrderManager()

    class Meta:
        verbose_name = "Sifariş"
        verbose_name_plural = "Sifarişlər 🍽️"

    def __str__(self):
        return f"Order {self.id} for {self.table}"

    def update_total_price(self):
        total_price = self.order_items.aggregate(
            total=Sum('price', output_field=models.DecimalField())
        )['total'] or Decimal(0)
        self.total_price = total_price
        self.save()

# Intermediate model for Order and Meal relationship


class OrderItemManager(models.Manager):
    def all_order_items(self):
        return super().get_queryset()

    def get_queryset(self):
        # Override the default queryset to exclude deleted objects
        return super().get_queryset().filter(order__is_deleted=False)


class OrderItem(DateTimeModel, models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="order_items",
        verbose_name="Sifariş"
    )
    # status = models.CharField(choices=(models.Choices()))
    meal = models.ForeignKey(
        Meal, on_delete=models.CASCADE, verbose_name="Yemək"
    )
    quantity = models.IntegerField(default=1, verbose_name="Miqdar")
    is_prepared = models.BooleanField(default=False)
    price = models.DecimalField(
        max_digits=9, decimal_places=2, default=0.00, verbose_name="Məbləğ"
    )
    is_deleted_by_adminstrator = models.BooleanField(default=False)
    item_added_at = models.DateTimeField(
        default=timezone.now, blank=True, null=True
    )

    customer_number = models.PositiveIntegerField(
        default=1,
        verbose_name="Müştəri №"
    )
    confirmed = models.BooleanField(default=False)

    history = HistoricalRecords()
    objects = OrderItemManager()

    class Meta:
        verbose_name = "Sifariş məhsulu"
        verbose_name_plural = "Sifariş məhsulları 🥘"

    def __str__(self):
        try:
            return f"Müştəri {self.customer_number}: {self.quantity} x {self.meal.name} | Qiymət: {self.quantity * self.meal.price}"
        except:
            return "Yemək Yoxdur"

    def delete(self, *args, reason=None, deleted_by=None, comment=None, **kwargs):
        """
        - Unconfirmed items: delete immediately, no logging/inventory action.
        - Confirmed items: must supply reason ('return' or 'waste');
          logs the deletion (with optional comment), and if reason=='return'
          returns ingredients to inventory.
        """
        # 1) Simple delete if not confirmed
        if not self.confirmed:
            return super().delete(*args, **kwargs)

        # 2) Validate reason
        if reason not in (
            OrderItemDeletionLog.REASON_RETURN,
            OrderItemDeletionLog.REASON_WASTE
        ):
            raise ValidationError(
                "Təsdiqlənmiş məhsulları silmək üçün reason='return' və ya 'waste' olmalıdır."
            )

        # 3) Capture waitress name
        waitress = self.order.waitress
        waitress_name = waitress.get_full_name() if waitress else ""

        # 4) Create the deletion log
        OrderItemDeletionLog.objects.create(
            order_id=self.order_id,
            order_item_id=self.pk,
            table_id=self.order.table_id,
            waitress_name=waitress_name,
            meal_name=str(self.meal.name),
            quantity=self.quantity,
            price=self.price,
            customer_number=self.customer_number,
            reason=reason,
            deleted_by=deleted_by,
            comment=comment,
            deleted_at=now()
        )

        # 5) Return inventory on 'return'
        if reason == OrderItemDeletionLog.REASON_RETURN:
            from apps.inventory_connector.signals import OrderItemInventoryManager

            OrderItemInventoryManager._process_mappings(self, operation='add')

        # 6) Finally delete the record
        return super().delete(*args, **kwargs)
