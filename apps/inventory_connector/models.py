from django.db import models
from apps.meals.models import Meal
from inventory.models import InventoryItem


class MealInventoryConnector(models.Model):
    """
    Yeməyi bir və ya bir neçə anbar məhsulu ilə əlaqələndirir və hər biri üçün istifadə miqdarını göstərir.
    """
    meal = models.OneToOneField(
        Meal,
        on_delete=models.CASCADE,
        related_name='inventory_connector',
        verbose_name="Yemək"
    )
    inventory_items = models.ManyToManyField(
        InventoryItem,
        through='MealInventoryMapping',
        verbose_name="Anbar Məhsulları"
    )

    def __str__(self):
        return f"Anbar əlaqəsi: {self.meal.name}"

    class Meta:
        verbose_name = "Yemək üçün anbar əlaqəsi"
        verbose_name_plural = "Yeməklərin anbar əlaqələri"


class MealInventoryMapping(models.Model):
    """
    Orta model: Bir yeməyin hazırlanması üçün istifadə olunan anbar məhsulunu və miqdarını göstərir.
    """
    connector = models.ForeignKey(
        MealInventoryConnector,
        on_delete=models.CASCADE,
        related_name='mappings',
        verbose_name="Anbar Əlaqəsi"
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='meal_mappings',
        verbose_name="Anbar Məhsulu"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Bu yeməyin 1 vahidi üçün istifadə olunan anbar məhsulunun miqdarı (məs: 0.200 kq)",
        verbose_name="Miqdar"
    )

    def __str__(self):
        return f"{self.connector.meal.name} üçün {self.inventory_item.name} - {self.quantity}"

    class Meta:
        verbose_name = "Yemək-Anbar Miqdarı Əlaqəsi"
        verbose_name_plural = "Yemək-Anbar Miqdarı Əlaqələri"
        unique_together = ('connector', 'inventory_item')
