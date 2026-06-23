from apps.tenants.context import get_current_restaurant


def filter_by_restaurant(queryset, restaurant=None):
    """Filter queryset by restaurant using the model's restaurant field or common paths."""
    restaurant = restaurant or get_current_restaurant()
    if restaurant is None:
        return queryset

    model = queryset.model
    if hasattr(model, 'restaurant_id'):
        return queryset.filter(restaurant=restaurant)
    if hasattr(model, 'room_id'):
        return queryset.filter(room__restaurant=restaurant)
    if hasattr(model, 'group_id'):
        return queryset.filter(group__restaurant=restaurant)
    if hasattr(model, 'category_id'):
        return queryset.filter(category__group__restaurant=restaurant)
    if hasattr(model, 'table_id'):
        return queryset.filter(table__room__restaurant=restaurant)
    if hasattr(model, 'order_id'):
        return queryset.filter(order__table__room__restaurant=restaurant)
    return queryset
