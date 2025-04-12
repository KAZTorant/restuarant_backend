from apps.meals.models import Meal
from apps.meals.models import MealCategory
from apps.meals.models import MealGroup


from django.contrib import admin


admin.site.register(MealGroup)
admin.site.register(MealCategory)


class MealAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
    )


admin.site.register(Meal, MealAdmin)
