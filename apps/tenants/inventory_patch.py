"""Inventory paketinə tenant dəstəyi (xarici kazza_inventory)."""

from apps.tenants.admin_utils import filter_queryset_by_restaurant, get_user_restaurant


def patch_inventory_models():
    try:
        from django.db import models
        from inventory.models import InventoryItem, InventryCategory, InventoryRecord, Supplier
    except ImportError:
        return False

    fk_kwargs = {
        'to': 'tenants.Restaurant',
        'on_delete': models.CASCADE,
        'related_name': '+',
        'verbose_name': 'Restoran',
        'null': True,
        'blank': True,
    }

    for model in (InventoryItem, InventryCategory, Supplier, InventoryRecord):
        if not hasattr(model, 'restaurant'):
            field = models.ForeignKey(**fk_kwargs)
            field.set_attributes_from_name('restaurant')
            model.add_to_class('restaurant', field)

    return True


def _patch_admin_queryset(model_admin):
    original_get_queryset = model_admin.get_queryset

    def get_queryset(self, request):
        qs = original_get_queryset(request)
        return filter_queryset_by_restaurant(qs, get_user_restaurant(request.user))

    model_admin.get_queryset = get_queryset.__get__(model_admin, model_admin.__class__)

    original_save = model_admin.save_model

    def save_model(self, request, obj, form, change):
        restaurant = get_user_restaurant(request.user)
        if not change and restaurant and hasattr(obj, 'restaurant_id') and not obj.restaurant_id:
            obj.restaurant = restaurant
        return original_save(request, obj, form, change)

    model_admin.save_model = save_model.__get__(model_admin, model_admin.__class__)


def patch_inventory_admin():
    try:
        from django.contrib import admin
        from inventory.models import InventoryItem, InventryCategory, InventoryRecord, Supplier
    except ImportError:
        return

    for model in (InventoryItem, InventryCategory, Supplier, InventoryRecord):
        if model in admin.site._registry:
            _patch_admin_queryset(admin.site._registry[model])
