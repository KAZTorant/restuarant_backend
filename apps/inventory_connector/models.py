from django.db import models
from django.core.exceptions import ValidationError
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
        verbose_name="Menu"
    )
    inventory_items = models.ManyToManyField(
        InventoryItem,
        through='MealInventoryMapping',
        verbose_name="Anbar Məhsulları"
    )

    def __str__(self):
        return f"Anbar əlaqəsi: {self.meal.name}"

    class Meta:
        verbose_name = "Menu üçün anbar əlaqəsi"
        verbose_name_plural = "Menuların anbar əlaqələri"


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
        help_text="Bir yeməyin hazırlanması üçün lazım olan məhsul miqdarı. Anbar məhsulunun ölçü vahidi nədirsə, həmin vahiddə daxil edin. Məsələn: pizza üçün 0.250 kq un (250 qram = 0.250 kq), kebab üçün 0.200 kq ət (200 qram = 0.200 kq)",
        verbose_name="Miqdar"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Anbar məhsulunun 1 vahidinin satış qiyməti. Ölçü vahidi kq-sa 1 kq qiyməti, litr-sə 1 litr qiyməti yazın. Məsələn: 1 kq un 3 AZN-dırsa 3 yazın.",
        verbose_name="Vahid Qiymət (AZN)"
    )

    def __str__(self):
        return f"{self.connector.meal.name} üçün {self.inventory_item.name} - {self.quantity}"
    
    def clean(self):
        """Validate model data"""
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({
                'quantity': 'Miqdar müsbət olmalıdır.'
            })
        if self.price is not None and self.price < 0:
            raise ValidationError({
                'price': 'Qiymət mənfi ola bilməz.'
            })

    class Meta:
        verbose_name = "Menu-Anbar Miqdarı Əlaqəsi"
        verbose_name_plural = "Menu-Anbar Miqdarı Əlaqələri"
        unique_together = ('connector', 'inventory_item')
