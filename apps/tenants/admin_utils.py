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
