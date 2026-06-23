from apps.tenants.context import get_current_restaurant


class TenantQuerySetMixin:
    """Filter queryset by current restaurant for models with a restaurant FK."""

    tenant_field = 'restaurant'

    def get_queryset(self):
        qs = super().get_queryset()
        restaurant = get_current_restaurant()
        if restaurant is not None and hasattr(qs.model, self.tenant_field):
            return qs.filter(**{self.tenant_field: restaurant})
        return qs


class TenantAdminMixin:
    """Scope admin list views to current restaurant; auto-set on create."""

    tenant_field = 'restaurant'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'restaurant_id') and request.user.restaurant_id:
            return qs.filter(**{self.tenant_field: request.user.restaurant})
        return qs.none()

    def save_model(self, request, obj, form, change):
        if (
            not change
            and hasattr(obj, self.tenant_field)
            and not getattr(obj, f'{self.tenant_field}_id', None)
            and not request.user.is_superuser
            and hasattr(request.user, 'restaurant_id')
            and request.user.restaurant_id
        ):
            setattr(obj, self.tenant_field, request.user.restaurant)
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if (
            not request.user.is_superuser
            and hasattr(request.user, 'restaurant_id')
            and request.user.restaurant_id
            and self.tenant_field in form.base_fields
        ):
            form.base_fields[self.tenant_field].widget.attrs['readonly'] = True
            form.base_fields[self.tenant_field].disabled = True
        return form
