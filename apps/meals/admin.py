from apps.printers.models.place import PreparationPlace
from django.contrib import messages
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from apps.meals.models import Meal
from apps.meals.models import MealCategory
from apps.meals.models import MealGroup
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME


from django.contrib import admin


admin.site.register(MealGroup)
admin.site.register(MealCategory)


class PreparationPlaceActionForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    preparation_place = forms.ModelChoiceField(
        queryset=PreparationPlace.objects.all(),
        required=True,
        label="Hazırlanma yeri"
    )


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'preparation_place',
                    'price', 'cost_price', 'marja_amount', 'marja_percentage']
    list_filter = ['category', 'preparation_place']
    search_fields = ['name', 'description']
    actions = ['set_preparation_place']
    readonly_fields = ['cost_price', 'marja_amount', 'marja_percentage']

    def cost_price(self, obj):
        """Calculate total cost price from inventory mappings"""
        try:
            connector = obj.inventory_connector
            total_cost = 0
            for mapping in connector.mappings.all():
                total_cost += mapping.quantity * mapping.price
            return f"{total_cost:.2f} AZN"
        except:
            return "0.00 AZN"
    cost_price.short_description = "Xərc Qiyməti"
    cost_price.admin_order_field = 'price'  # For sorting

    def marja_amount(self, obj):
        """Calculate marja amount (profit amount)"""
        try:
            connector = obj.inventory_connector
            total_cost = 0
            for mapping in connector.mappings.all():
                total_cost += mapping.quantity * mapping.price
            marja_amount = obj.price - total_cost
            return f"{marja_amount:.2f} AZN"
        except:
            return f"{obj.price:.2f} AZN"
    marja_amount.short_description = "Marja (Məbləğ)"
    marja_amount.admin_order_field = 'price'

    def marja_percentage(self, obj):
        """Calculate marja percentage"""
        try:
            connector = obj.inventory_connector
            total_cost = 0
            for mapping in connector.mappings.all():
                total_cost += mapping.quantity * mapping.price
            if obj.price > 0:
                marja_percentage = ((obj.price - total_cost) / obj.price) * 100
                return f"{marja_percentage:.1f}%"
            return "0.0%"
        except:
            return "100.0%"
    marja_percentage.short_description = "Marja (%)"
    marja_percentage.admin_order_field = 'price'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'set-preparation-place/',
                self.admin_site.admin_view(self.set_preparation_place_view),
                name='set_preparation_place',
            ),
        ]
        return custom_urls + urls

    def set_preparation_place(self, request, queryset):
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        return redirect(
            f"set-preparation-place/?ids={','.join(selected)}"
        )

    set_preparation_place.short_description = "Seçilmiş yeməklərə hazırlanma yeri təyin et"

    def set_preparation_place_view(self, request):
        ids = request.GET.get("ids", "")
        meal_ids = ids.split(",")
        meals = Meal.objects.filter(pk__in=meal_ids)

        if request.method == "POST":
            form = PreparationPlaceActionForm(request.POST)
            if form.is_valid():
                preparation_place = form.cleaned_data['preparation_place']
                meals.update(preparation_place=preparation_place)
                self.message_user(
                    request,
                    f"{meals.count()} yeməyə '{preparation_place}' təyin olundu.",
                    messages.SUCCESS
                )
                return redirect("admin:meals_meal_changelist")
        else:
            form = PreparationPlaceActionForm(
                initial={'_selected_action': ids})

        return render(request, "admin/set_preparation_place.html", {
            'meals': meals,
            'form': form,
            'title': "Hazırlanma yeri təyin et",
            'selected_ids': meal_ids,  # Pass as a list, not a string
        })
