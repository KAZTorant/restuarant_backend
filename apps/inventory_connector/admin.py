from django.contrib import admin
from apps.inventory_connector.models import MealInventoryConnector, MealInventoryMapping


class MealInventoryMappingInline(admin.TabularInline):
    model = MealInventoryMapping
    extra = 1
    verbose_name = "Yemək-Anbar Miqdarı Əlaqəsi"
    verbose_name_plural = "Yemək-Anbar Miqdarı Əlaqələri"
    fields = ('inventory_item', 'quantity', 'price')
    # Note: autocomplete_fields removed due to missing search_fields in InventoryItem admin


class MealInventoryConnectorAdmin(admin.ModelAdmin):
    list_display = ('meal', 'get_inventory_count')
    inlines = [MealInventoryMappingInline]
    search_fields = ('meal__name',)
    # Note: autocomplete_fields removed due to missing search_fields in Meal admin
    
    def get_inventory_count(self, obj):
        return obj.mappings.count()
    get_inventory_count.short_description = 'Anbar Məhsulu Sayı'


admin.site.register(MealInventoryConnector, MealInventoryConnectorAdmin)
