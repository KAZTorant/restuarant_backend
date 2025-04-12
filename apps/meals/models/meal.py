from django.db import models

from apps.commons.models import DateTimeModel


# Model for Meal Category
class MealCategory(DateTimeModel, models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

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

    class Meta:
        verbose_name = "Yemək"
        verbose_name_plural = "Yeməklər"

    def __str__(self):
        return self.name
