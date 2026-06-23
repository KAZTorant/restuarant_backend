from apps.tenants.admin_utils import (
    apply_tenant_to_form_data,
    enforce_tenant_on_instance,
    filter_queryset_by_restaurant,
    get_tenant_lookup,
    get_user_restaurant,
    scope_foreign_key_queryset,
    strip_field_from_fieldsets,
)
from apps.tenants.context import get_current_restaurant


class TenantQuerySetMixin:
    tenant_lookup = None

    def get_queryset(self):
        qs = super().get_queryset()
        restaurant = get_current_restaurant() or get_user_restaurant(
            getattr(self, 'request', None) and self.request.user
        )
        lookup = self.tenant_lookup or get_tenant_lookup(qs.model)
        return filter_queryset_by_restaurant(qs, restaurant, lookup)


class TenantAdminMixin:
    """Admin queryset + form FK-ləri restorana görə filtirləyir."""

    tenant_lookup = None
    tenant_field = 'restaurant'
    show_restaurant_in_list = True

    def _admin_restaurant(self, request):
        return get_user_restaurant(request.user)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        restaurant = self._admin_restaurant(request)
        lookup = self.tenant_lookup or get_tenant_lookup(qs.model)
        return filter_queryset_by_restaurant(qs, restaurant, lookup)

    def save_model(self, request, obj, form, change):
        enforce_tenant_on_instance(self, request, obj)
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        restaurant = self._admin_restaurant(request)
        if restaurant and db_field.name in (
            'restaurant', 'room', 'table', 'group', 'category', 'meal', 'printer',
            'waitress', 'started_by', 'ended_by', 'created_by', 'paid_by',
            'from_user', 'to_user', 'deleted_by', 'work_period_config',
            'preparation_place', 'connector',
        ):
            kwargs['queryset'] = scope_foreign_key_queryset(
                kwargs.get('queryset', db_field.remote_field.model.objects.all()),
                db_field.name,
                restaurant,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        restaurant = self._admin_restaurant(request)
        if restaurant:
            if db_field.name == 'orders':
                from apps.orders.models import Order
                kwargs['queryset'] = filter_queryset_by_restaurant(
                    kwargs.get('queryset', Order.objects.all()),
                    restaurant,
                    'table__room__restaurant',
                )
            elif db_field.name == 'statistics':
                from apps.orders.models import Statistics
                kwargs['queryset'] = filter_queryset_by_restaurant(
                    kwargs.get('queryset', Statistics.objects.all()),
                    restaurant,
                )
            elif db_field.name == 'preparation_places':
                from apps.printers.models import PreparationPlace
                kwargs['queryset'] = filter_queryset_by_restaurant(
                    kwargs.get('queryset', PreparationPlace.objects.all()),
                    restaurant,
                    'printer__restaurant',
                )
            elif db_field.name == 'groups':
                kwargs['queryset'] = kwargs.get('queryset', db_field.remote_field.model.objects.all())
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        model = self.model
        if (
            request.user.is_superuser
            and hasattr(model, 'restaurant_id')
            and 'restaurant' not in filters
        ):
            filters.insert(0, 'restaurant')
        elif (
            not request.user.is_superuser
            and 'restaurant' in filters
        ):
            filters = [f for f in filters if f != 'restaurant']
        return filters

    def get_list_display(self, request):
        display = list(super().get_list_display(request))
        if (
            request.user.is_superuser
            and self.show_restaurant_in_list
            and hasattr(self.model, 'restaurant_id')
            and 'restaurant' not in display
        ):
            display.insert(0, 'restaurant')
        elif (
            not request.user.is_superuser
            and 'restaurant' in display
            and not self.show_restaurant_in_list
        ):
            display = [d for d in display if d != 'restaurant']
        return display

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not hasattr(self.model, 'restaurant_id'):
            return fields
        if request.user.is_superuser:
            if 'restaurant' not in fields:
                fields = ['restaurant'] + fields
        else:
            fields = [f for f in fields if f != 'restaurant']
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not hasattr(self.model, 'restaurant_id'):
            return fieldsets

        if not request.user.is_superuser:
            return strip_field_from_fieldsets(fieldsets, 'restaurant')

        if any('restaurant' in (fs[1].get('fields') or ()) for fs in fieldsets):
            return fieldsets
        fieldsets = list(fieldsets)
        title, options = fieldsets[0]
        fields = list(options.get('fields', ()))
        if 'restaurant' not in fields:
            options = {**options, 'fields': ('restaurant',) + tuple(fields)}
            fieldsets[0] = (title, options)
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if (
            not request.user.is_superuser
            and hasattr(self.model, 'restaurant_id')
            and 'restaurant' not in readonly
        ):
            readonly.append('restaurant')
        return readonly
