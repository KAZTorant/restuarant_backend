from django.contrib import admin
from apps.inventory_connector.models import MealInventoryConnector, MealInventoryMapping


class MealInventoryMappingInline(admin.TabularInline):
    model = MealInventoryMapping
    extra = 1
    verbose_name = "Yemək-Anbar Miqdarı Əlaqəsi"
    verbose_name_plural = "Yemək-Anbar Miqdarı Əlaqələri"


class MealInventoryConnectorAdmin(admin.ModelAdmin):
    list_display = ('meal',)
    inlines = [MealInventoryMappingInline]
    search_fields = ('meal__name',)


admin.site.register(MealInventoryConnector, MealInventoryConnectorAdmin)
