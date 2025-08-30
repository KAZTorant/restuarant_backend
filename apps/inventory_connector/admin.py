from django.contrib import admin
from django import forms
from apps.inventory_connector.models import MealInventoryConnector, MealInventoryMapping


class MealInventoryMappingForm(forms.ModelForm):
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        label="Miqdar",
        help_text="Bir yeməyin hazırlanması üçün lazım olan məhsul miqdarı. Anbar məhsulunun ölçü vahidi nədirsə, həmin vahiddə daxil edin. Məsələn: pizza üçün 0.250 kq un (250 qram = 0.250 kq), kebab üçün 0.200 kq ət (200 qram = 0.200 kq)",
        widget=forms.NumberInput(attrs={
            'title': 'Anbar məhsulunun ölçü vahidi ilə daxil edin. 100 qram = 0.100 kq',
            'placeholder': 'məs: 0.250 (250 qram)',
            'step': '0.001'
        })
    )
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        label="Vahid Qiymət (AZN)",
        help_text="Anbar məhsulunun 1 vahidinin satış qiyməti. Ölçü vahidi kq-sa 1 kq qiyməti, litr-sə 1 litr qiyməti yazın. Məsələn: 1 kq un 3 AZN-dırsa 3 yazın.",
        widget=forms.NumberInput(attrs={
            'title': 'Məhsulun 1 vahidinin qiyməti. Məsələn: 1 kq = 3 AZN',
            'placeholder': 'məs: 3.00',
            'step': '0.001'
        })
    )
    
    class Meta:
        model = MealInventoryMapping
        fields = '__all__'


class MealInventoryMappingInline(admin.StackedInline):
    model = MealInventoryMapping
    form = MealInventoryMappingForm
    extra = 1
    verbose_name = "Menu-Anbar Miqdarı Əlaqəsi"
    verbose_name_plural = "Menu-Anbar Miqdarı Əlaqələri"
    fields = ('inventory_item', 'quantity', 'price')
    
    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }


class MealInventoryConnectorAdmin(admin.ModelAdmin):
    list_display = ('meal', 'get_meal_category', 'get_meal_price', 'get_inventory_count')
    inlines = [MealInventoryMappingInline]
    search_fields = ('meal__name', 'meal__category__name')
    list_filter = ('meal__category',)
    
    fields = ('meal',)
    
    def get_meal_category(self, obj):
        return obj.meal.category.name if obj.meal and obj.meal.category else "Yoxdur"
    get_meal_category.short_description = 'Kateqoriya'
    
    def get_meal_price(self, obj):
        return f"{obj.meal.price} AZN" if obj.meal else "Yoxdur"
    get_meal_price.short_description = 'Menu Qiyməti'
    
    def get_inventory_count(self, obj):
        return obj.mappings.count()
    get_inventory_count.short_description = 'Anbar Məhsulu Sayı'


admin.site.register(MealInventoryConnector, MealInventoryConnectorAdmin)
