from django.contrib import admin, messages
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME

from apps.printers.models.place import PreparationPlace
from apps.meals.models import Meal, MealCategory, MealGroup
from apps.tenants.admin_utils import filter_queryset_by_restaurant, get_user_restaurant
from apps.tenants.mixins import TenantAdminMixin


@admin.register(MealGroup)
class MealGroupAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'restaurant')
    search_fields = ('name', 'restaurant__name')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('restaurant')


@admin.register(MealCategory)
class MealCategoryAdmin(TenantAdminMixin, admin.ModelAdmin):
    tenant_lookup = 'group__restaurant'
    show_restaurant_in_list = False
    list_display = ('name', 'group', 'is_extra')
    list_filter = ('group', 'is_extra')
    search_fields = ('name', 'group__name', 'group__restaurant__name')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'group__restaurant')


class PreparationPlaceActionForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    preparation_places = forms.ModelMultipleChoiceField(
        queryset=PreparationPlace.objects.all(),
        required=True,
        label="Hazırlanma yerləri",
        help_text="Bir və ya bir neçə hazırlanma yeri seçin",
        widget=forms.CheckboxSelectMultiple
    )


@admin.register(Meal)
class MealAdmin(TenantAdminMixin, admin.ModelAdmin):
    tenant_lookup = 'category__group__restaurant'
    show_restaurant_in_list = False
    list_display = ['name', 'category', 'get_preparation_places_display',
                    'price', 'cost_price', 'marja_amount', 'marja_percentage']
    list_filter = ['category', 'preparation_places']
    search_fields = ['name', 'description', 'category__name', 'category__group__restaurant__name']
    actions = ['set_preparation_place']
    readonly_fields = ['cost_price', 'marja_amount', 'marja_percentage']
    filter_horizontal = ['preparation_places']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category',
            'category__group',
            'category__group__restaurant',
        )

    def get_preparation_places_display(self, obj):
        places = obj.get_all_preparation_places()
        if places:
            return ", ".join([place.name for place in places])
        return "-"
    get_preparation_places_display.short_description = "Hazırlanma Yerləri"

    def cost_price(self, obj):
        try:
            connector = obj.inventory_connector
            total_cost = 0
            for mapping in connector.mappings.all():
                total_cost += mapping.quantity * mapping.price
            return f"{total_cost:.2f} AZN"
        except Exception:
            return "0.00 AZN"
    cost_price.short_description = "Xərc Qiyməti"
    cost_price.admin_order_field = 'price'

    def marja_amount(self, obj):
        try:
            connector = obj.inventory_connector
            total_cost = 0
            for mapping in connector.mappings.all():
                total_cost += mapping.quantity * mapping.price
            marja_amount = obj.price - total_cost
            return f"{marja_amount:.2f} AZN"
        except Exception:
            if obj.price is not None:
                return f"{obj.price:.2f} AZN"
            return "0.00 AZN"
    marja_amount.short_description = "Marja (Məbləğ)"
    marja_amount.admin_order_field = 'price'

    def marja_percentage(self, obj):
        try:
            connector = obj.inventory_connector
            total_cost = 0
            for mapping in connector.mappings.all():
                total_cost += mapping.quantity * mapping.price
            if obj.price > 0:
                marja_percentage = ((obj.price - total_cost) / obj.price) * 100
                return f"{marja_percentage:.1f}%"
            return "0.0%"
        except Exception:
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
        restaurant = get_user_restaurant(request.user)
        meals = filter_queryset_by_restaurant(
            Meal.objects.filter(pk__in=meal_ids),
            restaurant,
            'category__group__restaurant',
        )

        if request.method == "POST":
            form = PreparationPlaceActionForm(request.POST)
            if form.is_valid():
                preparation_places = filter_queryset_by_restaurant(
                    form.cleaned_data['preparation_places'],
                    restaurant,
                    'printer__restaurant',
                )
                for meal in meals:
                    meal.preparation_places.set(preparation_places)

                places_names = ", ".join([place.name for place in preparation_places])
                self.message_user(
                    request,
                    f"{meals.count()} yeməyə '{places_names}' təyin olundu.",
                    messages.SUCCESS
                )
                return redirect("admin:meals_meal_changelist")
        else:
            form = PreparationPlaceActionForm(initial={'_selected_action': ids})
            form.fields['preparation_places'].queryset = filter_queryset_by_restaurant(
                PreparationPlace.objects.all(),
                restaurant,
                'printer__restaurant',
            )

        return render(request, "admin/set_preparation_place.html", {
            'meals': meals,
            'form': form,
            'title': "Hazırlanma yeri təyin et",
            'selected_ids': meal_ids,
        })
