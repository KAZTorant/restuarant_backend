from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.contrib.auth import get_user_model

from apps.commons.models import DateTimeModel, TenantModel
from apps.commons.validation import validate_unique_name

User = get_user_model()


class Room(TenantModel, DateTimeModel, models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Zal"
        verbose_name_plural = "Zallar"
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                'restaurant',
                name='unique_room_name_ci_per_restaurant',
            ),
        ]

    def __str__(self):
        return f"{self.restaurant} — {self.name}"

    def clean(self):
        super().clean()
        if not self.restaurant_id:
            return
        validate_unique_name(
            type(self).objects.filter(restaurant_id=self.restaurant_id),
            'name',
            self.name,
            'Bu restoranda eyni adlı zal artıq mövcuddur.',
            exclude_pk=self.pk,
        )


class Table(DateTimeModel, models.Model):
    number = models.CharField(max_length=10, blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)
    room = models.ForeignKey(
        Room,
        related_name='tables',
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        verbose_name = "Stol"
        verbose_name_plural = "Stollar"
        constraints = [
            models.UniqueConstraint(
                Lower('number'),
                'room',
                condition=Q(number__isnull=False) & ~Q(number=''),
                name='unique_table_number_ci_per_room',
            ),
        ]

    def __str__(self):
        if self.room_id:
            return f"{self.room.restaurant} — {self.room.name} — Stol {self.number or self.pk}"
        return f"Stol {self.number or self.pk}"

    def clean(self):
        super().clean()
        if not self.room_id or not self.number:
            return
        validate_unique_name(
            type(self).objects.filter(room_id=self.room_id),
            'number',
            self.number,
            'Bu zalda eyni nömrəli stol artıq mövcuddur.',
            exclude_pk=self.pk,
        )

    @property
    def waitress(self) -> User:
        order = self.current_order
        if order:
            return order.waitress
        return User.objects.none()

    @property
    def total_price(self):
        price = 0
        for order in self.current_orders:
            price += order.total_price
        return price

    @property
    def current_order(self):
        return self.orders.exclude(is_deleted=True).filter(is_paid=False, is_main=True).first()

    @property
    def current_orders(self):
        return self.orders.exclude(is_deleted=True).filter(is_paid=False)

    @property
    def assignable_table(self):
        return not self.orders.exclude(is_deleted=True).filter(is_paid=False).exists()

    def can_print_check(self):
        """
        Determines if the table has an active order 
        that hasn't had the check printed yet.

        Returns:
            can_print (bool): True if there is an active, 
            unpaid order with an unprinted check, False otherwise.
        """
        active_order = self.current_order
        return (
            active_order is not None and
            not active_order.is_check_printed and
            not active_order.is_paid
        )
