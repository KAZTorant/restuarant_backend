from django.core.exceptions import PermissionDenied
from django.db.models import Q

from apps.tenants.models import Restaurant

# Model adına görə queryset filter yolu (model._meta.model_name)
TENANT_LOOKUPS = {
    'user': 'restaurant',
    'shifthandover': 'restaurant',
    'whatsappconfig': 'restaurant',
    'room': 'restaurant',
    'table': 'room__restaurant',
    'mealgroup': 'restaurant',
    'mealcategory': 'group__restaurant',
    'meal': 'category__group__restaurant',
    'order': 'table__room__restaurant',
    'orderitem': 'order__table__room__restaurant',
    'statistics': 'restaurant',
    'withdrawnlist': 'restaurant',
    'summary': 'restaurant',
    'report': 'restaurant',
    'workperiodconfig': 'restaurant',
    'orderitemdeletionlog': 'deleted_by__restaurant',
    'payment': 'table__room__restaurant',
    'paymentmethod': 'payment__table__room__restaurant',
    'paymentcalculation': 'restaurant',
    'income': 'restaurant',
    'expense': 'restaurant',
    'printer': 'restaurant',
    'printgatewaylocation': 'restaurant',
    'preparationplace': 'printer__restaurant',
    'mealinventoryconnector': 'meal__category__group__restaurant',
    'mealinventorymapping': 'connector__meal__category__group__restaurant',
    'historicalorder': 'table__room__restaurant',
    'historicalorderitem': 'order__table__room__restaurant',
}

# FK sahələri admin formunda restorana görə filtirlənir
SCOPED_FOREIGN_KEYS = {
    'restaurant': 'pk',  # staff users only see their own restaurant
    'room': 'restaurant',
    'table': 'room__restaurant',
    'group': 'restaurant',
    'category': 'group__restaurant',
    'meal': 'category__group__restaurant',
    'printer': 'restaurant',
    'preparation_place': 'printer__restaurant',
    'preparation_places': 'printer__restaurant',
    'waitress': 'restaurant',
    'started_by': 'restaurant',
    'ended_by': 'restaurant',
    'created_by': 'restaurant',
    'paid_by': 'restaurant',
    'from_user': 'restaurant',
    'to_user': 'restaurant',
    'deleted_by': 'restaurant',
    'work_period_config': 'restaurant',
    'connector': 'meal__category__group__restaurant',
    'inventory_item': None,  # inventory paketi — ümumi
}


def get_user_restaurant(user):
    if user.is_superuser:
        return None
    if hasattr(user, 'restaurant_id') and user.restaurant_id:
        return user.restaurant
    return None


def user_belongs_to_restaurant(user, restaurant):
    if user.is_superuser or restaurant is None:
        return True
    user_restaurant = get_user_restaurant(user)
    return user_restaurant is not None and user_restaurant.pk == restaurant.pk


def resolve_restaurant_via_lookup(obj, lookup):
    """Walk a tenant lookup path (e.g. room__restaurant) from obj to Restaurant."""
    if not lookup:
        return None
    if lookup == 'restaurant' or lookup.endswith('.restaurant'):
        return getattr(obj, 'restaurant', None)
    parts = lookup.split('__')
    if parts[-1] != 'restaurant':
        return None
    current = obj
    for part in parts:
        if current is None:
            return None
        current = getattr(current, part, None)
    return current


def enforce_tenant_on_instance(model_admin, request, obj):
    """Force or validate tenant ownership for staff users."""
    if request.user.is_superuser:
        return

    restaurant = get_user_restaurant(request.user)
    if restaurant is None:
        return

    model = obj.__class__
    if hasattr(model, 'restaurant_id'):
        setattr(obj, 'restaurant', restaurant)
        return

    lookup = getattr(model_admin, 'tenant_lookup', None) or get_tenant_lookup(model)
    if not lookup:
        return

    related_restaurant = resolve_restaurant_via_lookup(obj, lookup)
    if related_restaurant is None:
        return
    if related_restaurant.pk != restaurant.pk:
        raise PermissionDenied('Seçilmiş qeyd sizin restorana aid deyil.')


def apply_tenant_to_form_data(model_admin, request, data):
    """Strip cross-tenant values from API payloads for staff users."""
    if request.user.is_superuser or not isinstance(data, dict):
        return data

    restaurant = get_user_restaurant(request.user)
    if restaurant is None:
        return data

    data = dict(data)
    if hasattr(model_admin.model, 'restaurant_id'):
        data['restaurant'] = str(restaurant.pk)
    return data


def strip_field_from_fieldsets(fieldsets, field_name):
    updated = []
    for title, options in fieldsets:
        fields = options.get('fields') or ()
        flat = []
        for item in fields:
            if isinstance(item, (list, tuple)):
                nested = tuple(f for f in item if f != field_name)
                if nested:
                    flat.append(nested)
            elif item != field_name:
                flat.append(item)
        if flat:
            updated.append((title, {**options, 'fields': tuple(flat)}))
    return tuple(updated)


def get_tenant_lookup(model):
    return TENANT_LOOKUPS.get(model._meta.model_name)


def filter_queryset_by_restaurant(queryset, restaurant, lookup=None):
    if restaurant is None:
        return queryset
    model = queryset.model
    lookup = lookup or get_tenant_lookup(model)

    if lookup:
        return queryset.filter(**{lookup: restaurant})

    if model._meta.model_name == 'receipt':
        return queryset.filter(
            Q(payment__table__room__restaurant=restaurant)
            | Q(orders__table__room__restaurant=restaurant)
        ).distinct()

    return queryset


def scope_foreign_key_queryset(queryset, field_name, restaurant):
    if restaurant is None:
        return queryset
    lookup = SCOPED_FOREIGN_KEYS.get(field_name)
    if lookup:
        return queryset.filter(**{lookup: restaurant})
    return queryset
