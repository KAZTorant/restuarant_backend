from django.db import models

from apps.commons.models import DateTimeModel, TenantModel
from apps.printers.models.place import PreparationPlace


class MealGroup(TenantModel, DateTimeModel, models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Yemək kateqoriyası qrupu"
        verbose_name_plural = "Yemək kateqoriyaları qrupları"

    def __str__(self):
        return self.name

# Model for Meal Category


class MealCategory(DateTimeModel, models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    group = models.ForeignKey(
        MealGroup, blank=True, null=True,
        on_delete=models.SET_NULL, related_name="categories"
    )
    is_extra = models.BooleanField(
        default=False, help_text="price will be sent from api"
    )

    class Meta:
        verbose_name = "Yemək kateqoriyası"
        verbose_name_plural = "Yemək kateqoriyaları"

    def __str__(self):
        return self.name


# Model for Meal
class Meal(DateTimeModel, models.Model):
    category = models.ForeignKey(
        MealCategory,
        related_name='meals',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    preparation_place = models.ForeignKey(
        PreparationPlace,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='meals_single',
        help_text="Deprecated: Use preparation_places instead"
    )
    preparation_places = models.ManyToManyField(
        PreparationPlace,
        blank=True,
        related_name='meals_multi',
        verbose_name="Hazırlanma Yerləri",
        help_text="Bu yemək üçün çap olunacaq hazırlanma yerləri"
    )

    class Meta:
        verbose_name = "Yemək"
        verbose_name_plural = "Yeməklər"

    def __str__(self):
        return f"{self.category.name if self.category else 'Kateqoriya yoxdur'} - {self.name} - {self.price} AZN"

    @property
    def is_extra(self):
        return self.category.is_extra if self.category else False

    def get_all_preparation_places(self):
        """
        Returns all preparation places for this meal.
        Combines the old single preparation_place field with the new preparation_places M2M field.
        """
        places = list(self.preparation_places.all())
        # Add the single preparation_place if it exists and is not already in the list
        if self.preparation_place and self.preparation_place not in places:
            places.append(self.preparation_place)
        return places
